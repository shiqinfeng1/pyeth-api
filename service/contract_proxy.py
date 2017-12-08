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

from crypto import privkey_to_addr, sign_transaction

DEFAULT_TIMEOUT = 60
DEFAULT_RETRY_INTERVAL = 3


class ContractProxy:
    def __init__(self, contract_address, abi, gas_price, gas_limit) -> None:
        self.web3 = Web3
        if self.web3.eth.defaultAccount == web3_empty:
            self.web3.eth.defaultAccount = self.web3.eth.accounts[0]
        self.address = contract_address
        self.abi = abi
        self.contract = self.web3.eth.contract(abi=self.abi, address=contract_address)
        self.gas_price = gas_price
        self.gas_limit = gas_limit

    def create_signed_transaction(self, privkey, func_name, args, nonce_offset=0, value=0):
        tx = self.create_transaction(func_name, args, nonce_offset, value)

        sign_transaction(tx, privkey, int(self.web3.version.network))
        return encode_hex(rlp.encode(tx))

    def create_transaction(self, privkey,func_name, args, nonce_offset=0, value=0):
        sender = privkey_to_addr(privkey)
        data = self.create_transaction_data(func_name, args)
        nonce = self.web3.eth.getTransactionCount(sender, 'pending') + nonce_offset
        tx = Transaction(nonce, self.gas_price, self.gas_limit, self.address, value, data)
        # v = CHAIN_ID according to EIP 155.
        tx.v = self.web3.version.network
        tx.sender = decode_hex(sender)
        return tx

    def create_transaction_data(self, func_name, args):
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
    
class TokenContractProxy(ContractProxy):
    def get_token_mint_event_blocking(
            self, user, from_block=0, to_block='latest',
            wait=DEFAULT_RETRY_INTERVAL, timeout=DEFAULT_TIMEOUT
    ):
        filters = {
            '_user': user,
        }
        return self.get_event_blocking(
            'Mint', from_block, to_block, filters, None, wait, timeout
        )
    def get_token_transfer_event_blocking(
            self, sender, receiver, from_block=0, to_block='latest',
            wait=DEFAULT_RETRY_INTERVAL, timeout=DEFAULT_TIMEOUT
    ):
        filters = {
            '_from': sender,
            '_to': receiver
        }
        return self.get_event_blocking(
            'Transfer', from_block, to_block, filters, None, wait, timeout
        )

class ManagerContractProxy(ContractProxy):
    def __init__(self, contract_address, abi, gas_price, gas_limit,
                 tester_mode=False):
        super().__init__(contract_address, abi, gas_price, gas_limit, tester_mode)

    def get_current_locked_token(self, sender, open_block_number):
        try:
            channel_info = self.contract.call().getChannelInfo(sender, open_block_number)
        except BadFunctionCallOutput:
            # attempt to get info on a channel that doesn't exist
            return None
        return channel_info[2]
    
    def get_token_locktoken_event_blocking(
            self, user, from_block=0, to_block='latest',
            wait=DEFAULT_RETRY_INTERVAL, timeout=DEFAULT_TIMEOUT
    ):
        filters = {
            '_user': user,
        }
        return self.get_event_blocking(
            'LogLockToken', from_block, to_block, filters, None, wait, timeout
        )
    def get_token_settletoken_event_blocking(
            self, user, from_block=0, to_block='latest',
            wait=DEFAULT_RETRY_INTERVAL, timeout=DEFAULT_TIMEOUT
    ):
        filters = {
            '_user': user,
        }
        return self.get_event_blocking(
            'LogSettleToken', from_block, to_block, filters, None, wait, timeout
        )