"""
import gevent
import rlp
from eth_utils import decode_hex, encode_hex
from ethereum.transactions import Transaction
from web3 import Web3
from web3.exceptions import BadFunctionCallOutput
from web3.formatters import input_filter_params_formatter, log_array_formatter
from web3.utils.empty import empty as web3_empty
from web3.utils.events import get_event_data
from web3.utils.filters import construct_event_filter_params


import contract_abi

DEFAULT_TIMEOUT = 60
DEFAULT_RETRY_INTERVAL = 3


class ContractProxy:
    def __init__(self, privkey, contract_file, contract_name, constructor_parameters, contract_address,  
    gas_price, gas_limit):
        self.web3 = Web3
        if self.web3.eth.defaultAccount == web3_empty:
            self.web3.eth.defaultAccount = self.web3.eth.accounts[0]

        self.abi = contract_abi.get_static_or_compile(
            get_contract_path(contract_file),
            contract_name)

        if contract_address == nil:
            self.address = deploy_contract(
                privkey,
                contract_file,
                contract_name,
                constructor_parameters,)
        else:
            self.address = contract_address

        self.contract = self.web3.eth.contract(abi=self.abi, address=self.address)
        self.gas_price = gas_price
        self.gas_limit = gas_limit

    def create_signed_transaction(self, privkey, func_name, args, nonce_offset=0, value=0):
        tx = self.create_transaction(func_name, args, nonce_offset, value)

        sign_transaction(tx, privkey, int(self.web3.version.network))
        return encode_hex(rlp.encode(tx))

    def create_transaction(self, privkey,func_name, args, nonce_offset=0, value=0):
        sender = privkey_to_addr(privkey)
        data = self.build_transaction_data(func_name, args)
        nonce = self.web3.eth.getTransactionCount(sender, 'pending') + nonce_offset
        tx = Transaction(nonce, self.gas_price, self.gas_limit, self.address, value, data)
        # v = CHAIN_ID according to EIP 155.
        tx.v = self.web3.version.network
        tx.sender = decode_hex(sender)
        return tx

    def build_transaction_data(self, func_name, args):
        data = self.contract._prepare_transaction(func_name, args)['data']
        return decode_hex(data)

    def get_logs(self, event_name, from_block=0, to_block='latest', filters=None):
        filter_kwargs = {
            'fromBlock': from_block,
            'toBlock': to_block,
            'address': self.address
        }
        event_abi = [i for i in self.abi if i['type'] == 'event' and i['name'] == event_name][0]
        assert event_abi
        filters = filters if filters else {}
        filter_ = construct_event_filter_params(event_abi, argument_filters=filters,
                                                **filter_kwargs)[1]
        filter_params = input_filter_params_formatter(filter_)
        if not self.tester_mode:
            response = self.web3._requestManager.request_blocking('eth_getLogs', [filter_params])
        else:
            filter_ = self.web3.eth.filter(filter_params)
            response = self.web3.eth.getFilterLogs(filter_.filter_id)
            self.web3.eth.uninstallFilter(filter_.filter_id)

        logs = log_array_formatter(response)
        logs = [dict(log) for log in logs]
        for log in logs:
            log['args'] = get_event_data(event_abi, log)['args']
        return logs

    def get_event_blocking(
            self, event_name, from_block=0, to_block='pending', filters=None, condition=None,
            wait=DEFAULT_RETRY_INTERVAL, timeout=DEFAULT_TIMEOUT
    ):
        for i in range(0, timeout + wait, wait):
            logs = self.get_logs(event_name, from_block, to_block, filters)
            matching_logs = [event for event in logs if not condition or condition(event)]
            if matching_logs:
                return matching_logs[0]
            elif i < timeout:
                if not self.tester_mode:
                    gevent.sleep(wait)
                else:
                    self.web3.eth.mine(1)

        return None
"""
# -*- coding: utf-8 -*-
from ethereum.abi import ContractTranslator
from ethereum.utils import normalize_address


class ContractProxy(object):
    """ Exposes a smart contract as a python object.

    Contract calls can be made directly in this object, all the functions will
    be exposed with the equivalent api and will perform the argument
    translation.
    """

    def __init__(self, sender, abi, address, call_func, transact_func, estimate_function=None):
        sender = normalize_address(sender)

        self.abi = abi
        self.address = address = normalize_address(address)
        self.translator = ContractTranslator(abi)

        for function_name in self.translator.function_data:
            function_proxy = MethodProxy(
                sender,
                address,
                function_name,
                self.translator,
                call_func,
                transact_func,
                estimate_function,
            )

            type_argument = self.translator.function_data[function_name]['signature']

            arguments = [
                '{type} {argument}'.format(type=type_, argument=argument)
                for type_, argument in type_argument
            ]
            function_signature = ', '.join(arguments)

            function_proxy.__doc__ = '{function_name}({function_signature})'.format(
                function_name=function_name,
                function_signature=function_signature,
            )

            setattr(self, function_name, function_proxy)


class MethodProxy(object):
    """ A callable interface that exposes a contract function. """
    valid_kargs = set(('gasprice', 'startgas', 'value'))

    def __init__(
            self,
            sender,
            contract_address,
            function_name,
            translator,
            call_function,
            transaction_function,
            estimate_function=None):

        self.sender = sender
        self.contract_address = contract_address
        self.function_name = function_name
        self.translator = translator
        self.call_function = call_function
        self.transaction_function = transaction_function
        self.estimate_function = estimate_function

    def transact(self, *args, **kargs):
        assert set(kargs.keys()).issubset(self.valid_kargs)
        data = self.translator.encode(self.function_name, args)

        txhash = self.transaction_function(
            sender=self.sender,
            to=self.contract_address,
            value=kargs.pop('value', 0),
            data=data,
            **kargs
        )

        return txhash

    def call(self, *args, **kargs):
        assert set(kargs.keys()).issubset(self.valid_kargs)
        data = self.translator.encode(self.function_name, args)

        res = self.call_function(
            sender=self.sender,
            to=self.contract_address,
            value=kargs.pop('value', 0),
            data=data,
            **kargs
        )

        if res:
            res = self.translator.decode(self.function_name, res)
            res = res[0] if len(res) == 1 else res
        return res

    def estimate_gas(self, *args, **kargs):
        if not self.estimate_function:
            raise RuntimeError('estimate_function was not supplied.')

        assert set(kargs.keys()).issubset(self.valid_kargs)
        data = self.translator.encode(self.function_name, args)

        res = self.estimate_function(
            sender=self.sender,
            to=self.contract_address,
            value=kargs.pop('value', 0),
            data=data,
            **kargs
        )

        return res

    def __call__(self, *args, **kargs):
        if self.translator.function_data[self.function_name]['is_constant']:
            result = self.call(*args, **kargs)
        else:
            result = self.transact(*args, **kargs)

        return result
