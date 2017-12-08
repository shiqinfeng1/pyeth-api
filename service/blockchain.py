# -*- coding: utf-8 -*-
from time import time as now

import rlp
import gevent
from gevent.lock import Semaphore
from ethereum import slogging

from ethereum.exceptions import InvalidTransaction
from ethereum.transactions import Transaction
from ethereum.utils import encode_hex, normalize_address
from pyethapp.jsonrpc import (
    address_encoder,
    address_decoder,
    data_decoder,
    data_encoder,
    default_gasprice,
)
from pyethapp.rpc_client import topic_encoder, JSONRPCClient, block_tag_encoder
import requests

from ethereum.utils import denoms
import util


GAS_LIMIT = 3141592  # Morden's gasLimit.
GAS_PRICE = denoms.shannon * 20

log = slogging.getLogger(__name__)  # pylint: disable=invalid-name

# Coding standard for this module:
#
# - Be sure to reflect changes to this module in the test
#   implementations. [tests/utils/*_client.py]
# - Expose a synchronous interface by default
#   - poll for the transaction hash
#   - check if the proper events were emited
#   - use `call` and `transact` to interact with pyethapp.rpc_client proxies


class JSONRPCPollTimeoutException(Exception):
    # FIXME import this from pyethapp.rpc_client once it is implemented
    pass

"""检查交易是否失败"""
def check_transaction_threw(client, transaction_hash):
    """Check if the transaction threw or if it executed properly"""
    encoded_transaction = data_encoder(transaction_hash.decode('hex'))
    transaction = client.call('eth_getTransactionByHash', encoded_transaction)
    receipt = client.call('eth_getTransactionReceipt', encoded_transaction)
    return int(transaction['gas'], 0) == int(receipt['gasUsed'], 0)


def decode_topic(topic):
    return int(topic[2:], 16)


class BlockChainService(object):
    """ Exposes the blockchain's state through JSON-RPC. """
    # pylint: disable=too-many-instance-attributes

    def __init__(
            self,
            chain_name,
            host,
            port):
            
        self.chain_name = chain_name
        self.host = host
        self.port = port

    def estimate_blocktime(self, oldest=256):
        """Calculate a blocktime estimate based on some past blocks.
        Args:
            oldest (int): delta in block numbers to go back.
        Return:
            average block time (int) in seconds
        """
        last_block_number = self.block_number()
        # around genesis block there is nothing to estimate
        if last_block_number < 1:
            return 15
        # if there are less than `oldest` blocks available, start at block 1
        if last_block_number < oldest:
            interval = (last_block_number - 1) or 1
        else:
            interval = last_block_number - oldest
        assert interval > 0
        last_timestamp = int(self.get_block_header(last_block_number)['timestamp'], 16)
        first_timestamp = int(self.get_block_header(last_block_number - interval)['timestamp'], 16)
        delta = last_timestamp - first_timestamp
        return float(delta) / interval

    def next_block(self):
        target_block_number = self.block_number() + 1
        current_block = target_block_number

        while not current_block >= target_block_number:
            current_block = self.block_number()
            gevent.sleep(0.5)

        return current_block

    