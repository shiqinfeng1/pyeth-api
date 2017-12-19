import os
import click
from binascii import hexlify, unhexlify
from service.blockchain import (
    BlockChainService,
)
import gevent
from service import accounts_manager

from service.utils import (
    address_decoder,
    split_endpoint,
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

@click.command()
@click.option('--eth', default='localhost:8545', help='<ip:port> of ethereum client.')
@click.option('--quorum', prompt='localhost:40001', help='<ip:port> of quorum client.')
def demo(eth,quorum):
    
    h1,p1=split_endpoint(eth)
    h2,p2=split_endpoint(quorum)
    """connect to ethereum client"""
    ethereum_proxy = blockchain_service.new_blockchain_proxy(
        'ethereum_proxy', h1,p1,os.getcwd()+'/keystore')

    quorum_proxy = blockchain_service.new_blockchain_proxy(
        'quorum_proxy', h2,p2,os.getcwd()+'/keystore')
    
    """test users"""
    owner =  '0xa1629411f4e8608a7bb88e8a7700f11c59175e72'
    user_1 = '0x63f1de588c7ce855b66cf24b595a8991f921130d'
    user_2 = '0x5252781539b365e08015fa7ed77af5a36097f39d'

    """test transfer eth, executed twice in succession"""
    print '111111111111111111111111111111111111111111111111'
    txhash=ethereum_proxy.transfer_eth(
        sender=owner,to=user_1,eth_amount=321,password='123456') # first execution needs password to unlock
    ethereum_proxy.poll_contarct_transaction_result(txhash)

    txhash=quorum_proxy.transfer_eth(
        sender=owner,to=user_1,eth_amount=123,password='123456')
    quorum_proxy.poll_contarct_transaction_result(txhash)

    """test deploy contract"""
    print '222222222222222222222222222222222222222222222222'
    ERC223Token_ethereum_owner = ethereum_proxy.deploy_contract( 
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
        (hexlify(ERC223Token_ethereum_owner.address),)
        )

    print '333333333333333333333333333333333333333333333333'
    """contract operation method 1: get_contract_proxy """
    ERC223Token_etheteum_owner = ethereum_proxy.get_contract_proxy(owner,'ERC223Token')
    block_number = ethereum_proxy.block_number()
    txhash = ERC223Token_etheteum_owner.mint(user_1,1111) #test mint token to user_1
    txhash = ERC223Token_etheteum_owner.transfer(user_2,11*WEI_TO_ETH,'')
    txhash = ERC223Token_etheteum_owner.transfer(user_2,22*WEI_TO_ETH,'')
    ethereum_proxy.poll_contarct_transaction_result(txhash,block_number,ERC223Token_etheteum_owner,'Minted',user_1) # wait until transaction is comfired
    ethereum_proxy.poll_contarct_transaction_result(txhash,block_number,ERC223Token_etheteum_owner,'Transfer',owner,user_2)

    """contract operation method 2: attach_contract """
    print '444444444444444444444444444444444444444444444444'
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
        ERC223Token_quorum_owner,
        TokenExchange_etheteum_owner.sender, 
        4*WEI_TO_ETH
        )

    """ test print all accounts & balance """
    print '5555555555555555555555555555555555555555555555555'
    addresses = list(ethereum_proxy.account_manager.accounts.keys())
    for idx, addr in enumerate(addresses):
        print("[{:3d}]ethereum account: 0x{} \nbalance:{} ETH \nbalance:{} REX"
            .format(idx, addr,
            ethereum_proxy.balance(address_decoder(addr))/WEI_TO_ETH,
            ERC223Token_ethereum_owner.balanceOf(addr)/WEI_TO_ETH))
        print("[{:3d}]quorum account: 0x{} \nbalance:{} ETH \nbalance:{} REX"
            .format(idx, addr,
            ethereum_proxy.balance(address_decoder(addr))/WEI_TO_ETH,
            ERC223Token_quorum_owner.balanceOf(addr)/WEI_TO_ETH))

if __name__ == '__main__':
    slogging.configure(':DEBUG')
    demo()
