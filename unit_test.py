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


if __name__ == '__main__':
    slogging.configure(':DEBUG')
    demo()
