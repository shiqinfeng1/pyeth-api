from pyethapi.service.contract_proxy import ContractProxy


class TokenContractEvents(object):
    def get_transfer_event_blocking(to):
        ContractProxy.events_filter(rpcclient, contract_address, topics, from_block=0, to_block='pending')
        BlockchainEvents.get_contract_events_blocking()
http://lib.csdn.net/article/python/1704