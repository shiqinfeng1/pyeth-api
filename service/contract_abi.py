import os
import json
import hashlib
import warnings
from ethereum import _solidity
from ethereum.utils import sha3, is_string, encode_hex, remove_0x_head, to_string
from utils import get_contract_path


def contract_checksum(contract_path):
    with open(contract_path) as f:
        checksum = hashlib.sha1(f.read()).hexdigest()
        return checksum

def get_static_or_compile(
        contract_path,
        contract_name,
        **compiler_flags):
    """Search the path of `contract_path` for a file with the same name and the
    extension `.static-abi.json`. If the file exists, and the recorded checksum
    matches, this will return the precompiled contract, otherwise it will
    compile it.

    Writing compiled contracts to the desired file and path happens only when
    the environment variable `STORE_PRECOMPILED` is set (to whatever value).
    Users are not expected to ever set this value, the functionality is exposed
    through the `setup.py compile_contracts` command.

    Args:
        contract_path (str): the path of the contract file
        contract_name (str): the contract name
        **compiler_flags (dict): flags that will be passed to the compiler
    """
    # this will be set by `setup.py compile_contracts`
    store_updated = os.environ.get('STORE_PRECOMPILED', False)
    precompiled = None
    precompiled_path = '{}.static-abi.json'.format(contract_path)
    try:
        with open(precompiled_path) as f:
            precompiled = json.load(f)
    except IOError:
        pass

    if precompiled or store_updated:
        checksum = contract_checksum(contract_path)
    if precompiled and precompiled['checksum'] == checksum:
        return precompiled
    if _solidity.get_solidity() is None:
        raise RuntimeError("The solidity compiler, `solc`, is not available.")
    compiled = _solidity.compile_contract(
        contract_path,
        contract_name,
        combined='abi'
    )
    if store_updated:
        compiled['checksum'] = checksum
        with open(precompiled_path, 'w') as f:
            json.dump(compiled, f)
        print("'{}' written".format(precompiled_path))
    return compiled

def get_abi(
        contract_file,
        contract_name):
    registry_compiled = get_static_or_compile(
        get_contract_path(contract_file),
        contract_name,
        combined='abi',
    )
    return registry_compiled['abi']

class ContractTranslator(object):
    
    def __init__(self, contract_interface):
        if is_string(contract_interface):
            contract_interface = json_decode(contract_interface)

        self.fallback_data = None
        self.constructor_data = None
        self.function_data = {}
        self.event_data = {}

        for description in contract_interface:
            entry_type = description.get('type', 'function')
            encode_types = []
            signature = []

            # If it's a function/constructor/event
            if entry_type != 'fallback' and 'inputs' in description:
                encode_types = [
                    element['type']
                    for element in description.get('inputs')
                ]

                signature = [
                    (element['type'], element['name'])
                    for element in description.get('inputs')
                ]

            if entry_type == 'function':
                normalized_name = normalize_name(description['name'])

                decode_types = [
                    element['type']
                    for element in description['outputs']
                ]

                self.function_data[normalized_name] = {
                    'prefix': method_id(normalized_name, encode_types),
                    'encode_types': encode_types,
                    'decode_types': decode_types,
                    'is_constant': description.get('constant', False),
                    'signature': signature,
                    'payable': description.get('payable', False),
                }

            elif entry_type == 'event':
                normalized_name = normalize_name(description['name'])

                indexed = [
                    element['indexed']
                    for element in description['inputs']
                ]
                names = [
                    element['name']
                    for element in description['inputs']
                ]
                # event_id == topics[0]
                self.event_data[event_id(normalized_name, encode_types)] = {
                    'types': encode_types,
                    'name': normalized_name,
                    'names': names,
                    'indexed': indexed,
                    'anonymous': description.get('anonymous', False),
                }

            elif entry_type == 'constructor':
                if self.constructor_data is not None:
                    raise ValueError('Only one constructor is supported.')

                self.constructor_data = {
                    'encode_types': encode_types,
                    'signature': signature,
                }

            elif entry_type == 'fallback':
                if self.fallback_data is not None:
                    raise ValueError('Only one fallback function is supported.')
                self.fallback_data = {'payable': description['payable']}

            else:
                raise ValueError('Unknown type {}'.format(description['type']))

    def encode(self, function_name, args):
        warnings.warn('encode is deprecated, please use encode_function_call', DeprecationWarning)
        return self.encode_function_call(function_name, args)

    def decode(self, function_name, data):
        warnings.warn('decode is deprecated, please use decode_function_result', DeprecationWarning)
        return self.decode_function_result(function_name, data)

    def encode_function_call(self, function_name, args):
        """ Return the encoded function call.

        Args:
            function_name (str): One of the existing functions described in the
                contract interface.
            args (List[object]): The function arguments that wll be encoded and
                used in the contract execution in the vm.

        Return:
            bin: The encoded function name and arguments so that it can be used
                 with the evm to execute a funcion call, the binary string follows
                 the Ethereum Contract ABI.
        """
        if function_name not in self.function_data:
            raise ValueError('Unkown function {}'.format(function_name))

        description = self.function_data[function_name]

        function_selector = zpad(encode_int(description['prefix']), 4)
        arguments = encode_abi(description['encode_types'], args)

        return function_selector + arguments

    def decode_function_result(self, function_name, data):
        """ Return the function call result decoded.

        Args:
            function_name (str): One of the existing functions described in the
                contract interface.
            data (bin): The encoded result from calling `function_name`.

        Return:
            List[object]: The values returned by the call to `function_name`.
        """
        description = self.function_data[function_name]
        arguments = decode_abi(description['decode_types'], data)
        return arguments

    def encode_constructor_arguments(self, args):
        """ Return the encoded constructor call. """
        if self.constructor_data is None:
            raise ValueError("The contract interface didn't have a constructor")

        return encode_abi(self.constructor_data['encode_types'], args)

    def decode_event(self, log_topics, log_data):
        """ Return a dictionary representation the log.

        Note:
            This function won't work with anonymous events.

        Args:
            log_topics (List[bin]): The log's indexed arguments.
            log_data (bin): The encoded non-indexed arguments.
        """
        # https://github.com/ethereum/wiki/wiki/Ethereum-Contract-ABI#function-selector-and-argument-encoding

        # topics[0]: keccak(EVENT_NAME+"("+EVENT_ARGS.map(canonical_type_of).join(",")+")")
        # If the event is declared as anonymous the topics[0] is not generated;
        if not len(log_topics) or log_topics[0] not in self.event_data:
            raise ValueError('Unknown log type')

        event_id_ = log_topics[0]

        event = self.event_data[event_id_]

        # data: abi_serialise(EVENT_NON_INDEXED_ARGS)
        # EVENT_NON_INDEXED_ARGS is the series of EVENT_ARGS that are not
        # indexed, abi_serialise is the ABI serialisation function used for
        # returning a series of typed values from a function.
        unindexed_types = [
            type_
            for type_, indexed in zip(event['types'], event['indexed'])
            if not indexed
        ]
        unindexed_args = decode_abi(unindexed_types, log_data)

        # topics[n]: EVENT_INDEXED_ARGS[n - 1]
        # EVENT_INDEXED_ARGS is the series of EVENT_ARGS that are indexed
        indexed_count = 1  # skip topics[0]

        result = {}
        for name, type_, indexed in zip(event['names'], event['types'], event['indexed']):
            if indexed:
                topic_bytes = utils.zpad(
                    utils.encode_int(log_topics[indexed_count]),
                    32,
                )
                indexed_count += 1
                value = decode_single(process_type(type_), topic_bytes)
            else:
                value = unindexed_args.pop(0)

            result[name] = value
        result['_event_type'] = utils.to_string(event['name'])

        return result

    def listen(self, log, noprint=True):
        """
        Return a dictionary representation of the Log instance.

        Note:
            This function won't work with anonymous events.

        Args:
            log (processblock.Log): The Log instance that needs to be parsed.
            noprint (bool): Flag to turn off priting of the decoded log instance.
        """
        try:
            result = self.decode_event(log.topics, log.data)
        except ValueError:
            return  # api compatibility

        if not noprint:
            print(result)

        return result