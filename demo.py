import os
from service.blockchain import (
    BlockChainService,
)
from service import accounts_manager
import custom_contract_proxy
from service.utils import (
    address_decoder,
)
from  service.constant import (
    WEI_TO_ETH
)
from ethereum import slogging

def demo():
    poa1 = BlockChainService(
        'poa1', '192.168.1.5','8545',os.getcwd()+'/keystore')
    poa2 = BlockChainService(
        'poa2', '192.168.1.5','8545',os.getcwd()+'/keystore')
    
    """transfer eth, executed twice in succession"""
    poa1.transfer_eth(
        '0xa1629411f4e8608a7bb88e8a7700f11c59175e72',
        '0x63f1de588c7ce855b66cf24b595a8991f921130d',
        123333,
        '123456')
    
    poa1.transfer_eth(
        '0xa1629411f4e8608a7bb88e8a7700f11c59175e72',
        '0x5252781539b365e08015fa7ed77af5a36097f39d',
        123333,
        '123456')
    
    poa1.deploy_contract( 
        '0xa1629411f4e8608a7bb88e8a7700f11c59175e72', 
        'ERC223Token.sol', 
        'ERC223Token',
        (
            100000,
            'REX',
            18,
            'REX Token'
        ),)

    """ print all accounts & balance """
    addresses = list(poa1.account_manager.accounts.keys())
    for idx, addr in enumerate(addresses):
        print("[{:3d}]account: 0x{} balance:{} ETH"
            .format(idx, addr,poa1.balance(address_decoder(addr))/WEI_TO_ETH)) 


if __name__ == '__main__':
    slogging.configure(':DEBUG')
    demo()
