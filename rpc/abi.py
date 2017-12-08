import os
import json
import hashlib

from ethereum import _solidity
from ethereum.abi import event_id, normalize_name, ContractTranslator

from utils import get_contract_path

__all__ = (
    'REGISTRY_ABI',
    'TOKENADDED_EVENT',
    'TOKENADDED_EVENTID',
    'REGISTRY_TRANSLATOR'
)

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


registry_compiled = get_static_or_compile(
    get_contract_path('Registry.sol'),
    'Registry',
    combined='abi',
)
REGISTRY_ABI = registry_compiled['abi']
