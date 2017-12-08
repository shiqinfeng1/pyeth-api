# -*- coding: utf-8 -*-
from time import time as now

import rlp
import gevent
from gevent.lock import Semaphore
from ethereum import slogging
from ethereum import _solidity
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

"""
from raiden.blockchain.abi import (
    TOKENADDED_EVENTID,
    CHANNEL_MANAGER_ABI,
    CHANNELNEW_EVENTID,
    ENDPOINT_REGISTRY_ABI,
    HUMAN_TOKEN_ABI,
    NETTING_CHANNEL_ABI,
    REGISTRY_ABI,
)
"""
DEFAULT_POLL_TIMEOUT = 180
GAS_LIMIT = 3141592  # Morden's gasLimit.
GAS_PRICE = denoms.shannon * 20

log = slogging.getLogger(__name__)  # pylint: disable=invalid-name
solidity = _solidity.get_solidity()  # pylint: disable=invalid-name

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

""""""
def patch_send_transaction(client, nonce_offset=0):
    """Check if the remote supports pyethapp's extended jsonrpc spec for local tx signing.
    If not, replace the `send_transaction` method with a more generic one.
    """
    patch_necessary = False

    try:
        client.call('eth_nonce', encode_hex(client.sender), 'pending')
    except:
        patch_necessary = True
        client.last_nonce_update = 0
        client.current_nonce = None
        client.nonce_lock = Semaphore()

    def send_transaction(sender, to, value=0, data='', startgas=GAS_LIMIT,
                         gasprice=GAS_PRICE, nonce=None):
        """Custom implementation for `pyethapp.rpc_client.JSONRPCClient.send_transaction`.
        This is necessary to support other remotes that don't support pyethapp's extended specs.
        @see https://github.com/ethereum/pyethapp/blob/develop/pyethapp/rpc_client.py#L359
        """
        def get_nonce():
            """Eventually syncing nonce counter.
            This will keep a local nonce counter that is only syncing against
            the remote every `UPDATE_INTERVAL`.

            If the remote counter is lower than the current local counter,
            it will wait for the remote to catch up.
            """
            with client.nonce_lock:
                UPDATE_INTERVAL = 5.
                query_time = now()
                needs_update = abs(query_time - client.last_nonce_update) > UPDATE_INTERVAL
                not_initialized = client.current_nonce is None
                if needs_update or not_initialized:
                    nonce = _query_nonce()
                    # we may have hammered the server and not all tx are
                    # registered as `pending` yet
                    while nonce < client.current_nonce:
                        log.debug(
                            "nonce on server too low; retrying",
                            server=nonce,
                            local=client.current_nonce
                        )
                        nonce = _query_nonce()
                        query_time = now()
                    client.current_nonce = nonce
                    client.last_nonce_update = query_time
                else:
                    client.current_nonce += 1
                return client.current_nonce

        def _query_nonce():
            pending_transactions_hex = client.call(
                'eth_getTransactionCount',
                address_encoder(sender),
                'pending',
            )
            pending_transactions = int(pending_transactions_hex, 16)
            nonce = pending_transactions + nonce_offset
            return nonce

        nonce = get_nonce()

        tx = Transaction(nonce, gasprice, startgas, to, value, data)
        assert hasattr(client, 'privkey') and client.privkey
        tx.sign(client.privkey)
        result = client.call(
            'eth_sendRawTransaction',
            data_encoder(rlp.encode(tx)),
        )
        return result[2 if result.startswith('0x') else 0:]

    if patch_necessary:
        client.send_transaction = send_transaction


def patch_send_message(client, pool_maxsize=50):
    """Monkey patch fix for issue #253. This makes the underlying `tinyrpc`
    transport class use a `requests.session` instead of regenerating sessions
    for each request.

    See also: https://github.com/mbr/tinyrpc/pull/31 for a proposed upstream
    fix.

    Args:
        client (pyethapp.rpc_client.JSONRPCClient): the instance to patch
        pool_maxsize: the maximum poolsize to be used by the `requests.Session()`
    """
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_maxsize=pool_maxsize)
    session.mount(client.transport.endpoint, adapter)

    def send_message(message, expect_reply=True):
        if not isinstance(message, str):
            raise TypeError('str expected')

        r = session.post(
            client.transport.endpoint,
            data=message,
            **client.transport.request_kwargs
        )

        if expect_reply:
            return r.content

    client.transport.send_message = send_message


def new_filter(jsonrpc_client, contract_address, topics, from_block=None, to_block=None):
    """ Custom new filter implementation to handle bad encoding from geth rpc. """
    if isinstance(from_block, int):
        from_block = hex(from_block)
    if isinstance(to_block, int):
        to_block = hex(to_block)
    json_data = {
        'fromBlock': from_block if from_block is not None else 'latest',
        'toBlock': to_block if to_block is not None else 'latest',
        'address': address_encoder(normalize_address(contract_address)),
    }

    if topics is not None:
        json_data['topics'] = [
            topic_encoder(topic)
            for topic in topics
        ]

    return jsonrpc_client.call('eth_newFilter', json_data)


def decode_topic(topic):
    return int(topic[2:], 16)

# 发送合约调用
def estimate_and_transact(classobject, callobj, *args):
    """Estimate gas using eth_estimateGas. Multiply by 2 to make sure sufficient gas is provided
    Limit maximum gas to GAS_LIMIT to avoid exceeding blockgas limit
    """
    estimated_gas = callobj.estimate_gas(
        *args,
        startgas=classobject.startgas,
        gasprice=classobject.gasprice
    )
    estimated_gas = min(estimated_gas * 2, GAS_LIMIT)
    transaction_hash = callobj.transact(
        *args,
        startgas=estimated_gas,
        gasprice=classobject.gasprice
    )
    return transaction_hash


class BlockChainService(object):
    """ Exposes the blockchain's state through JSON-RPC. """
    # pylint: disable=too-many-instance-attributes

    def __init__(
            self,
            privatekey_bin,
            registry_address,
            host,
            port,
            poll_timeout=DEFAULT_POLL_TIMEOUT,
            **kwargs):

        self.address_token = dict()
        self.address_discovery = dict()
        self.address_manager = dict()
        self.address_contract = dict()
        self.address_registry = dict()
        self.token_manager = dict()

        # 新建一个连接到节点的客户端, 指定账户是privatekey_bin
        jsonrpc_client = JSONRPCClient(
            privkey=privatekey_bin,
            host=host,
            port=port,
            print_communication=True,
        )
        # 检查send_transaction和send_message接口, 必要的话自定义接口
        patch_send_transaction(jsonrpc_client)
        patch_send_message(jsonrpc_client)

        self.client = jsonrpc_client
        self.private_key = privatekey_bin
        self.node_address = privatekey_to_address(privatekey_bin)
        self.poll_timeout = poll_timeout

    def set_verbosity(self, level):
        if level:
            self.client.print_communication = True

    def block_number(self):
        return self.client.blocknumber()

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

    def get_block_header(self, block_number):
        block_number = block_tag_encoder(block_number)
        return self.client.call('eth_getBlockByNumber', block_number, False)

    def next_block(self):
        target_block_number = self.block_number() + 1
        current_block = target_block_number

        while not current_block >= target_block_number:
            current_block = self.block_number()
            gevent.sleep(0.5)

        return current_block

    def deploy_contract(self, contract_name, contract_file, constructor_parameters=None):
        contract_path = get_contract_path(contract_file)
        contracts = _solidity.compile_file(contract_path, libraries=dict())

        log.info(
            'Deploying "%s" contract',
            contract_file,
        )

        proxy = self.client.deploy_solidity_contract(
            self.node_address,
            contract_name,
            contracts,
            dict(),
            constructor_parameters,
            contract_path=contract_path,
            gasprice=default_gasprice,
            timeout=self.poll_timeout,
        )
        return proxy.address