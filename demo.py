import os
from service.blockchain import (
    BlockChainService,
)
import gevent
from service import accounts_manager

from service.utils import (
    address_decoder,
)
from  service.constant import (
    WEI_TO_ETH
)
from ethereum import slogging

blockchain_service = BlockChainService()


def lock_token(srcTokenProxy, destTokenProxy, TokenExchangeAddress, lockAmount):
    txhash = srcTokenProxy.transfer(
        TokenExchangeAddress,lockAmount*WEI_TO_ETH,'')
    txhash = destTokenProxy.mint(
        srcTokenProxy.sender,lockAmount*WEI_TO_ETH)

def demo():
    
    """connect to ethereum client"""
    ethereum_proxy = blockchain_service.new_blockchain_proxy(
        'ethereum_proxy', '192.168.20.141','8545',os.getcwd()+'/keystore')

    quorum_proxy = blockchain_service.new_blockchain_proxy(
        'quorum_proxy', '192.168.20.141','8544',os.getcwd()+'/keystore')
    
    """test users"""
    owner =  '0xa1629411f4e8608a7bb88e8a7700f11c59175e72'
    user_1 = '0x63f1de588c7ce855b66cf24b595a8991f921130d'
    user_2 = '0x5252781539b365e08015fa7ed77af5a36097f39d'

    """test transfer eth, executed twice in succession"""
    ethereum_procy.transfer_eth(
        sender=owner,to=user_1,eth_amount=123333,password='123456') # first execution needs password to unlock
    quorum_proxy.transfer_eth(
        sender=owner,to=user_1,eth_amount=123333)

    """test deploy contract"""
    ERC223Token_ethereum = ethereum_proxy.deploy_contract( 
        owner, 
        'ERC223Token.sol', 'ERC223Token',
        (100000,'REX',18,'REX Token')
        )
    ERC223Token_quorum_owner = quorum_proxy.deploy_contract( 
        owner, 
        'ERC223Token.sol', 'ERC223Token',
        (100000,'REX',18,'REX Token')
        )
    TokenExchange = ethereum_proxy.deploy_contract( 
        owner, 
        'TokenExchange.sol', 'TokenExchange',
        (contract_proxy.address)
        )

    """contract operation method 1: get_contract_proxy """
    ERC223Token_etheteum_owner = ethereum_proxy.get_contract_proxy(owner,'ERC223Token')
    block_number = ethereum_proxy.block_number()
    txhash = ERC223Token_etheteum_owner.mint(user_1,1111) #test mint token to user_1
    txhash = ERC223Token_etheteum_owner.transfer(user_2,11*WEI_TO_ETH,'')
    txhash = ERC223Token_etheteum_owner.transfer(user_2,22*WEI_TO_ETH,'')
    ethereum_proxy.poll_contarct_transaction_result(block_number,ERC223Token_1,txhash,'Minted',user_1) # wait until transaction is comfired
    ethereum_proxy.poll_contarct_transaction_result(block_number,ERC223Token_1,txhash,'Transfer',user_1,user_2)

    """contract operation method 2: attach_contract """
    TokenExchange_etheteum_owner = ethereum_proxy.attach_contract(
        owner,
        TokenExchange.address,
        'TokenExchange.sol','TokenExchange','123456')
    ERC223Token_etheteum_user1 = ethereum_proxy.attach_contract(
        user_1,
        TokenExchange.address,
        'ERC223Token.sol','ERC223Token','123456')
    
    lock_token(
        ERC223Token_etheteum_user1,
        TokenExchange_etheteum_owner.sender, 
        ERC223Token_quorum_owner
        )

    """ test print all accounts & balance """
    addresses = list(ethereum_proxy.account_manager.accounts.keys())
    for idx, addr in enumerate(addresses):
        print("[{:3d}]account: 0x{} \nbalance:{} ETH \nbalance:{} REX"
            .format(idx, addr,
            ethereum_proxy.balance(address_decoder(addr))/WEI_TO_ETH,
            ERC223Token_1.balanceOf(addr)/WEI_TO_ETH))

if __name__ == '__main__':
    slogging.configure(':DEBUG')
    demo()
