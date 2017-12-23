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
    address_encoder,
    split_endpoint,
)
from  service.constant import (
    WEI_TO_ETH
)
from ethereum import slogging

blockchain_service = BlockChainService()
BLACKHOLE_ADDRESS= '0x0000000000000000000000000000000000000009'

@click.command()
@click.option('--eth', default='localhost:8545', help='<ip:port> of ethereum client.')
@click.option('--quorum', prompt='localhost:40001', help='<ip:port> of quorum client.')
def token_exchange(eth,quorum):
    print "\n======\n解析链地址"
    h1,p1=split_endpoint(eth)
    h2,p2=split_endpoint(quorum)

    print "\n======\n生成链代理"
    ethereum_proxy = blockchain_service.new_blockchain_proxy(
        'ethereum_proxy', h1,p1,os.getcwd()+'/pyethapi/keystore')

    quorum_proxy = blockchain_service.new_blockchain_proxy(
        'quorum_proxy', h2,p2,os.getcwd()+'/pyethapi/keystore')
    
    print "\n======\n配置测试账户"
    admin =  '0xa1629411f4e8608a7bb88e8a7700f11c59175e72'
    advister = '0x63f1de588c7ce855b66cf24b595a8991f921130d'
    scaner = '0x5252781539b365e08015fa7ed77af5a36097f39d'

    print "\n======\n检查账户eth余额"
    assert ethereum_proxy.balance(address_decoder(admin))/WEI_TO_ETH > 1
    assert quorum_proxy.balance(address_decoder(admin))/WEI_TO_ETH > 1

    print "\n======\n部署合约..."
    ERC223Token_ethereum_owner = ethereum_proxy.deploy_contract( 
        admin,  # 部署者
        'ERC223Token.sol', 'ERC223Token', # 合约文件, 合约名字
        (100000,'REX',18,'REX Token'),  # 合约参数
        '123456')
    ERC223Token_quorum_owner = quorum_proxy.deploy_contract( 
        admin, 
        'ERC223Token.sol', 'ERC223Token',
        (100000,'REX',18,'REX Token'),
        '123456')
    TokenExchange_ethereum_owner = ethereum_proxy.deploy_contract( 
        admin, 
        'TokenExchange.sol', 'TokenExchange',
        (hexlify(ERC223Token_ethereum_owner.address),)
        )

    print "\n======\n给 advister 铸造 1111 个token"
    block_number = ethereum_proxy.block_number()
    txhash = ERC223Token_ethereum_owner.mint(advister,1111)
    ethereum_proxy.poll_contarct_transaction_result(txhash,block_number,ERC223Token_ethereum_owner,'Minted',advister) 

    print "\n======\nadviser关联到ethereum上的token合约"
    ERC223Token_eth_advister = ethereum_proxy.attach_contract(
        advister,
        ERC223Token_ethereum_owner.address,
        'ERC223Token.sol','ERC223Token','123456')

    print "\n======\nadviser进行锁定操作: 将 11 个token发给TokenExchange合约"
    block_number = ethereum_proxy.block_number()
    txhash = ERC223Token_eth_advister.transfer(
        TokenExchange_ethereum_owner.address,11*WEI_TO_ETH,'')
    ethereum_proxy.poll_contarct_transaction_result(
        txhash,block_number,TokenExchange_ethereum_owner,'LogLockToken',advister)
    
    print "\n======\n在quorum上给adviser铸造相应数量的token"
    block_number = quorum_proxy.block_number()
    txhash = ERC223Token_quorum_owner.mint(advister,11)
    quorum_proxy.poll_contarct_transaction_result(
        txhash,block_number,ERC223Token_quorum_owner,'Minted',advister) 

    print "\n======\nadviser关联到quorum上的token合约"
    ERC223Token_quorum_advister = quorum_proxy.attach_contract(
        advister,
        ERC223Token_quorum_owner.address,
        'ERC223Token.sol','ERC223Token','123456')

    print "\n======\nadvister分发3个token给扫码者"
    block_number = quorum_proxy.block_number()
    txhash = ERC223Token_quorum_advister.transfer(
        scaner,3*WEI_TO_ETH,'')
    quorum_proxy.poll_contarct_transaction_result(
        txhash,block_number,ERC223Token_quorum_advister,'Transfer',advister,scaner)

    print "\n======\n扫码者结算2个token"
    settleAmount = 2
    if settleAmount > ERC223Token_quorum_owner.balanceOf(scaner)/WEI_TO_ETH:
        raise ValueError('insufficient token balance of {}'.format(scaner))
    ERC223Token_quorum_scaner = quorum_proxy.attach_contract(
        scaner,
        ERC223Token_quorum_owner.address,
        'ERC223Token.sol','ERC223Token','123456')
    block_number = quorum_proxy.block_number()
    txhash = ERC223Token_quorum_scaner.transfer(
        BLACKHOLE_ADDRESS,settleAmount*WEI_TO_ETH,'')
    quorum_proxy.poll_contarct_transaction_result(
        txhash,block_number,ERC223Token_quorum_scaner,'Transfer',scaner,BLACKHOLE_ADDRESS)

    block_number = ethereum_proxy.block_number()
    txhash = TokenExchange_ethereum_owner.settleToken(scaner,settleAmount*WEI_TO_ETH)
    ethereum_proxy.poll_contarct_transaction_result(txhash,block_number,TokenExchange_ethereum_owner,'LogSettleToken',scaner)

    print "\n======\n检查最终结果"
    name=['advister','scaner','admin',]
    addresses = list(ethereum_proxy.account_manager.accounts.keys())
    for idx, addr in enumerate(addresses):
        print("[{:2d} {}]ethereum account: 0x{} \nbalance:{} ETH \nbalance:{} REX"
            .format(idx, name[idx], addr,
            ethereum_proxy.balance(address_decoder(addr))/WEI_TO_ETH,
            ERC223Token_ethereum_owner.balanceOf(addr)/WEI_TO_ETH))
        print("[{:2d} {}]quorum account: 0x{} \nbalance:{} ETH \nbalance:{} REX"
            .format(idx, name[idx], addr,
            quorum_proxy.balance(address_decoder(addr))/WEI_TO_ETH,
            ERC223Token_quorum_owner.balanceOf(addr)/WEI_TO_ETH))
    
    print("[TokenExchange] {} \nbalance:{} ETH \nbalance:{} REX"
            .format(address_encoder(TokenExchange_ethereum_owner.address),
            ethereum_proxy.balance(TokenExchange_ethereum_owner.address)/WEI_TO_ETH,
            ERC223Token_ethereum_owner.balanceOf(TokenExchange_ethereum_owner.address)/WEI_TO_ETH))
    
if __name__ == '__main__':
    slogging.configure(':DEBUG')
    token_exchange()