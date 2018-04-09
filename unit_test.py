# -*- coding: utf-8 -*-
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
    WEI_TO_ETH,
    ATM_DECIMALS,
)
from ethereum import slogging

blockchain_service = BlockChainService()

@click.command()
@click.option('--eth', default='localhost:8545', help='<ip:port> of ethereum client.')
@click.option('--atmchain', prompt='localhost:40001', help='<ip:port> of atmchain client.')
def demo(eth,atmchain):
    
    h1,p1=split_endpoint(eth)
    h2,p2=split_endpoint(atmchain)
    """connect to ethereum client"""
    ethereum_proxy = blockchain_service.new_blockchain_proxy(
        'ethereum_proxy', h1,p1,os.getcwd()+'/keystore')

    atmchain_proxy = blockchain_service.new_blockchain_proxy(
        'atmchain_proxy', h2,p2,os.getcwd()+'/keystore')
    
    """users for tests"""
    owner =  '0xa1629411f4e8608a7bb88e8a7700f11c59175e72'
    user_1 = '0x63f1de588c7ce855b66cf24b595a8991f921130d'
    user_2 = '0x5252781539b365e08015fa7ed77af5a36097f39d'

    """test transfer eth, executed twice in succession"""
    print '111111111111111111111111111111111111111111111111'
    txhash=ethereum_proxy.transfer_eth(
        sender=owner,to=user_1,eth_amount=321,password='123456') # first execution needs password to unlock
    ethereum_proxy.poll_contarct_transaction_result(txhash)

    txhash=atmchain_proxy.transfer_eth(
        sender=owner,to=user_1,eth_amount=123,password='123456')
    atmchain_proxy.poll_contarct_transaction_result(txhash)

    """test deploy contract"""
    print '222222222222222222222222222222222222222222222222'
    ERC223Token_ethereum_owner = ethereum_proxy.deploy_contract( 
        owner, 
        'ERC223Token.sol', 'ERC223Token',
        (100000,'REX',18,'REX Token')
        )
    ERC223Token_atmchain_owner = atmchain_proxy.deploy_contract( 
        owner, 
        'ERC223Token.sol', 'ERC223Token',
        (100000,'REX',18,'REX Token')
        )
    TokenExchange_ethereum_owner = ethereum_proxy.deploy_contract( 
        owner, 
        'TokenExchange.sol', 'TokenExchange',
        (hexlify(ERC223Token_ethereum_owner.address),)
        )

    print '333333333333333333333333333333333333333333333333'
    """contract operation method 1: get_contract_proxy """
    ERC223Token_eth_owner = ethereum_proxy.get_contract_proxy(owner,'ERC223Token')
    block_number = ethereum_proxy.block_number()
    txhash = ERC223Token_eth_owner.mint(user_1,1111) #test mint token to user_1
    txhash = ERC223Token_eth_owner.transfer(user_2,11*ATM_DECIMALS,'')
    txhash = ERC223Token_eth_owner.transfer(user_2,22*ATM_DECIMALS,'')
    ethereum_proxy.poll_contarct_transaction_result(txhash,block_number,ERC223Token_eth_owner,'Minted',user_1) # wait until transaction is comfired
    ethereum_proxy.poll_contarct_transaction_result(txhash,block_number,ERC223Token_eth_owner,'Transfer',owner,user_2)

    """contract operation method 2: attach_contract """
    print '444444444444444444444444444444444444444444444444'
    TokenExchange_eth_owner = ethereum_proxy.attach_contract(
        owner,
        TokenExchange.address,
        'TokenExchange.sol','TokenExchange','123456')
    ERC223Token_eth_user1 = ethereum_proxy.attach_contract(
        user_1,
        ERC223Token_ethereum_owner.address,
        'ERC223Token.sol','ERC223Token','123456')

    """ test print all accounts & balance """
    print '5555555555555555555555555555555555555555555555555'
    addresses = list(ethereum_proxy.account_manager.accounts.keys())
    for idx, addr in enumerate(addresses):
        print("[{:3d}]ethereum account: 0x{} \nbalance:{} ETH \nbalance:{} REX"
            .format(idx, addr,
            ethereum_proxy.balance(address_decoder(addr))/WEI_TO_ETH,
            ERC223Token_ethereum_owner.balanceOf(addr)/ATM_DECIMALS))
        print("[{:3d}]atmchain account: 0x{} \nbalance:{} ETH \nbalance:{} REX"
            .format(idx, addr,
            ethereum_proxy.balance(address_decoder(addr))/WEI_TO_ETH,
            ERC223Token_atmchain_owner.balanceOf(addr)/ATM_DECIMALS))

if __name__ == '__main__':
    slogging.configure(':DEBUG')
    demo()
