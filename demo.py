import os
from service.blockchain import (
    BlockChainService,
)
import gevent
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
        'poa1', '192.168.20.141','8545',os.getcwd()+'/keystore')
    poa2 = BlockChainService(
        'poa2', '192.168.20.141','8545',os.getcwd()+'/keystore')
    
    """transfer eth, executed twice in succession"""
    owner = '0xa1629411f4e8608a7bb88e8a7700f11c59175e72'
    user_1 = '0x63f1de588c7ce855b66cf24b595a8991f921130d'
    user_2 = '0x5252781539b365e08015fa7ed77af5a36097f39d'
    poa1.transfer_eth(
        owner,
        user_1,
        123333,
        '123456')
    
    poa1.transfer_eth(
        owner,
        user_2,
        123333)
    
    poa1.deploy_contract( 
        owner, 
        'ERC223Token.sol', 
        'ERC223Token',
        (
            100000,
            'REX',
            18,
            'REX Token'
        ))

    ERC223Token_1 = poa1.get_contract_proxy(owner,'ERC223Token')
    ERC223Token_1.mint(user_1,1233)

    ERC223Token_2 = poa1.get_contract_proxy(user_1,'ERC223Token','123456')
    ERC223Token_2.transfer(user_2,111)
    gevent.sleep(20)

    """ print all accounts & balance """
    addresses = list(poa1.account_manager.accounts.keys())
    for idx, addr in enumerate(addresses):
        print("[{:3d}]account: 0x{} \nbalance:{} ETH \nbalance:{} REX"
            .format(idx, addr,
            poa1.balance(address_decoder(addr))/WEI_TO_ETH,
            ERC223Token_2.balanceOf(addr)))


if __name__ == '__main__':
    slogging.configure(':DEBUG')
    demo()
