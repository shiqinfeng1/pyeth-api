from service.contract_proxy import ContractProxy
from ethereum.utils import denoms

GAS_PRICE = denoms.shannon * 20
GAS_LIMIT = 3141592
"""
class TokenContractProxy(ContractProxy):

    def __init__(self, 
                privkey, contract_file, contract_name, constructor_parameters, 
                contract_address, 
                gas_price = GAS_PRICE, gas_limit = GAS_LIMIT):
        super().__init__(
                privkey, contract_file, contract_name, constructor_parameters, 
                contract_address, 
                gas_price, gas_limit)

    def get_token_mint_event_blocking(
            self, user, 
            from_block=0, to_block='latest',wait=DEFAULT_RETRY_INTERVAL, timeout=DEFAULT_TIMEOUT
    ):
        filters = {
            '_user': user,
        }
        return self.get_event_blocking(
            'Mint', from_block, to_block, filters, None, wait, timeout
        )
    def get_token_transfer_event_blocking(
            self, sender, receiver, 
            from_block=0, to_block='latest',wait=DEFAULT_RETRY_INTERVAL, timeout=DEFAULT_TIMEOUT
    ):
        filters = {
            '_from': sender,
            '_to': receiver
        }
        return self.get_event_blocking(
            'Transfer', from_block, to_block, filters, None, wait, timeout
        )

class ManagerContractProxy(ContractProxy):
    
    def __init__(self, 
                privkey, contract_file, contract_name, constructor_parameters, 
                contract_address, 
                gas_price = GAS_PRICE, gas_limit = GAS_LIMIT):
        super().__init__(
                privkey, contract_file, contract_name, constructor_parameters, 
                contract_address, 
                gas_price, gas_limit)

    def get_current_locked_token(self, sender, open_block_number):
        try:
            channel_info = self.contract.call().getChannelInfo(sender, open_block_number)
        except BadFunctionCallOutput:
            # attempt to get info on a channel that doesn't exist
            return None
        return channel_info[2]
    
    def get_token_locktoken_event_blocking(
            self, user, 
            from_block=0, to_block='latest',wait=DEFAULT_RETRY_INTERVAL, timeout=DEFAULT_TIMEOUT
    ):
        filters = {
            '_user': user,
        }
        return self.get_event_blocking(
            'LogLockToken', from_block, to_block, filters, None, wait, timeout
        )
    def get_token_settletoken_event_blocking(
            self, user, 
            from_block=0, to_block='latest', wait=DEFAULT_RETRY_INTERVAL, timeout=DEFAULT_TIMEOUT
    ):
        filters = {
            '_user': user,
        }
        return self.get_event_blocking(
            'LogSettleToken', from_block, to_block, filters, None, wait, timeout
        )
"""