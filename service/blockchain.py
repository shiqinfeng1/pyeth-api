# -*- coding: utf-8 -*-
from time import time as now
import os
import sys
import rlp
import re
import warnings
import gevent
from gevent.lock import Semaphore
from ethereum import slogging
from ethereum.abi import ContractTranslator
from ethereum.exceptions import InvalidTransaction
from ethereum.transactions import Transaction
from ethereum.utils import encode_hex, normalize_address
from pyethapp.jsonrpc import (
    data_encoder,
)
from pyethapp.rpc_client import deploy_dependencies_symbols, dependencies_order_of_build
from service.utils import (
    split_endpoint,
)
from rlp.utils import decode_hex
import json

from exceptions import (
    EthNodeCommunicationError,
)
from ethereum._solidity import (
    solidity_unresolved_symbols,
    solidity_library_symbol,
    solidity_resolve_symbols,
    compile_file
)
from binascii import hexlify, unhexlify
import requests
import constant
from tinyrpc.transports.http import HttpPostClientTransport
from tinyrpc.exc import InvalidReplyError
from tinyrpc.protocols.jsonrpc import (
    JSONRPCErrorResponse,
    JSONRPCProtocol,
    JSONRPCSuccessResponse,
)
from contract_proxy import ContractProxy
from utils import (
    address_decoder,
    address_encoder,
    block_tag_encoder,
    data_decoder,
    data_encoder,
    privatekey_to_address,
    quantity_decoder,
    quantity_encoder,
    topic_encoder,
    topic_decoder,
    timeout_two_stage,
    get_contract_path,
    bool_decoder,
)

import accounts_manager
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

def check_node_connection(func):
    """ A decorator to reconnect if the connection to the node is lost """
    def retry_on_disconnect(self, *args, **kwargs):
        for i, timeout in enumerate(timeout_two_stage(10, 3, 10)):
            try:
                result = func(self, *args, **kwargs)
                if i > 0:
                    log.info('Client reconnected')
                return result

            except (requests.exceptions.ConnectionError, InvalidReplyError):
                log.info(
                    'Timeout in eth client connection. Is the client offline? Trying '
                    'again in {}s.'.format(timeout)
                )
            gevent.sleep(timeout)

    return retry_on_disconnect

"""检查客户端通信是否正常"""
def check_json_rpc(client):
    try:
        client_version = client.call('web3_clientVersion')
    except (requests.exceptions.ConnectionError, EthNodeCommunicationError):
        print(
            "\n"
            "Couldn't contact the ethereum node through JSON-RPC.\n"
            "Please make sure the JSON-RPC is enabled for these interfaces:\n"
            "\n"
            "    eth_*, net_*, web3_*\n"
            "\n"
            "geth: https://github.com/ethereum/go-ethereum/wiki/Management-APIs\n"
        )
        return False
    else:
        if client_version.startswith('Parity'):
            major, minor, patch = [
                int(x) for x in re.search(r'//v(\d+)\.(\d+)\.(\d+)', client_version).groups()
            ]
            if (major, minor, patch) < (1, 7, 6):
                print('You need Byzantium enabled parity. >= 1.7.6 / 1.8.0')
                return False
        elif client_version.startswith('Geth'):
            major, minor, patch = [
                int(x) for x in re.search(r'/v(\d+)\.(\d+)\.(\d+)', client_version).groups()
            ]
            if (major, minor, patch) < (1, 7, 2):
                print('You need Byzantium enabled geth. >= 1.7.2')
                return False
        else:
            print('Unsupported client {} detected.'.format(client_version))
            return False

    return True

"""链服务：新建链代理，及获取链代理"""
class BlockChainService(object):
    
    def __init__(self):      
        self.blockchain_proxy =  dict()

    """新建链代理"""
    def new_blockchain_proxy(self,
            chain_name,
            endpoint,
            keystore_path):
        
        self.blockchain_proxy[chain_name] = BlockChainProxy(
            chain_name,
            endpoint,
            keystore_path)
        if self.blockchain_proxy[chain_name] == None:
            raise RuntimeError('create BlockChainProxy fail.')

        return self.blockchain_proxy[chain_name]
    
    """获取链代理"""
    def get_blockchain_proxy(self,chain_name):
        if self.blockchain_proxy[chain_name] == None:
            log.info("blockchain {} not registered!".format(chain_name))
            return None
        return self.blockchain_proxy[chain_name]

class BlockChainProxy(object):
    """ Exposes the blockchain's state through JSON-RPC. """

    def __init__(
            self,
            chain_name,
            endpoint,
            keystore_path):
            
        self.chain_name = chain_name
        self.local_contract_proxys =  dict()
        self.jsonrpc_proxys =  dict()
        self.account_manager = accounts_manager.AccountManager(keystore_path)
        self.third_party_endpoint = None
        self.host = None
        self.port = None
        
        """如果是第三方节点地址"""
        if endpoint in ['mainnet', 'ropsten', 'kovan', 'rinkeby']:
            self.third_party_endpoint  = 'https://'+endpoint+'.infura.io/SaTkK9e9TKrRuhHg'
            self.jsonrpc_client_without_sender = JSONRPCClient_for_infura(
                self.third_party_endpoint,
                '',
            )
        else:
            self.host, self.port = split_endpoint(endpoint)
            self.jsonrpc_client_without_sender = JSONRPCClient(
                self.host,
                self.port,
                '',
            )
            if not check_json_rpc(self.jsonrpc_client_without_sender):
                raise RuntimeError('BlockChainProxy connect eth-client fail.')

    def get_jsonrpc_client_with_sender(self, sender, password=None):
        if sender == None:
            return None
        if self.jsonrpc_proxys.get(sender) == None:
            private_key = self.account_manager.get_account(sender,password).privkey

            if len(hexlify(private_key)) != 64:
                private_key = decode_hex(private_key)

            if self.third_party_endpoint == None:
                self.jsonrpc_proxys[sender] = JSONRPCClient(
                    host = self.host,
                    port = self.port,
                    privkey = private_key,
                )
            else:
                self.jsonrpc_proxys[sender] = JSONRPCClient_for_infura(
                    self.third_party_endpoint,
                    privkey = private_key,
                )
        return self.jsonrpc_proxys[sender]

    def attach_contract(self, 
            contract_name,contract_file=None, contract_address=None,
            attacher=None,password=None):
        if attacher != None:
            client = self.get_jsonrpc_client_with_sender(attacher,password)
        else:
            client = self.jsonrpc_client_without_sender

        if client == None:
            log.info("jsoon rpc client is nil.")
            return None

        """检查是否为本代理部署的合约"""
        contract_local = self.local_contract_proxys.get(contract_name)
        if contract_local != None:
            if contract_local.sender == attacher: #是本地部署的合约，如果部署这是attacher，直接返回搞proxy
                return contract_local
            if contract_address != None and contract_address != contract_local.address: #是本地部署的合约，但合约地址不匹配
                log.info('Contract address has no match. deploy lastest contract first.')
                return None
            #是本地部署的合约，但没有指定合约地址，则从proxy中获取
            contract_address = contract_local.address
            abi = contract_local.abi
        elif contract_address != None: #非本代理部署的合约，但是指定了合约地址，编译该合约获取abi,并关联到合约地址
            deployed_code = client.eth_getCode(contract_address)
            if deployed_code == '0x':
                log.info('Contract address has no code. deploy contract first.')
                return None

            """编译合约"""
            contract_path=get_contract_path(contract_file)
            all_contracts = compile_file(contract_path, libraries=dict())
            if contract_name in all_contracts:
                contract_key = contract_name

            elif contract_path is not None:
                _, filename = os.path.split(contract_path)
                contract_key = filename + ':' + contract_name

                if contract_key not in all_contracts:
                    log.info('Unknown contract {}'.format(contract_name))
                    return None
            else:
                log.info('Unknown contract {} and no contract_path given'.format(contract_name))
                return None
            abi = all_contracts[contract_key]['abi']

        else: #非本代理部署的合约，但是没指定合约地址
            log.info('{} is NOT deployed in LOCAL and contract address is NULL. deploy contract first.'.format(contract_name))
            return None
        return client.new_contract_proxy(
            contract_name,
            abi,
            contract_address,
        )
    
    """检查交易是否失败"""
    def check_transaction_threw(self,transaction_hash):
        """Check if the transaction threw or if it executed properly"""
        encoded_transaction = data_encoder(transaction_hash.decode('hex'))
        transaction = self.jsonrpc_client_without_sender.call('eth_getTransactionByHash', encoded_transaction)
        receipt = self.jsonrpc_client_without_sender.call('eth_getTransactionReceipt', encoded_transaction)
        return int(transaction['gas'], 0) == int(receipt['gasUsed'], 0)

    """查询交易执行结果，并监听合约事件"""
    def poll_contarct_transaction_result(self,
        transaction_hash,
        fromBlock=0,
        contract_proxy=None,
        event_name=None,*event_filter_args):

        event_key=None
        event=None
        """等待交易被打包进入区块"""
        self.jsonrpc_client_without_sender.poll(
            unhexlify(transaction_hash),
            timeout=constant.DEFAULT_POLL_TIMEOUT,
        )
        """检查交易是否失败"""
        fail = self.check_transaction_threw(transaction_hash)
        if fail:
            log.info('transaction({}) execute failed .'.format(transaction_hash))
            return "transaction execute failed", list(transaction_hash)

        """如果指定监听合约事件，过滤该合约事件"""
        if event_name != None and contract_proxy != None:
            event_key,event = contract_proxy.poll_contract_event(
                fromBlock,
                event_name,constant.DEFAULT_TIMEOUT, True,
                *event_filter_args)
        return event_key, event    

    """部署合约"""    
    def deploy_contract(self, 
        sender, contract_file, contract_name,
        constructor_parameters=tuple(),
        password=None):

        client = self.get_jsonrpc_client_with_sender(sender,password)
        if client == None:
            return

        path = get_contract_path(contract_file)
        workdir, filename = os.path.split(path)
        log.info('\ndeploying contract: {}. Paras:{}. \nsender: {}. \nworkdir: {}.\n'.format(
            contract_name,constructor_parameters,sender,path))
        all_contracts = compile_file(path, libraries=dict())
        contract_proxy = client.deploy_solidity_contract(
            unhexlify(sender[2:]),
            contract_name, #contract_name
            all_contracts, #all_contracts
            dict(),  #libraries dict()
            constructor_parameters, #constructor_parameters tuple() (p1, p2, p3, p4)
            contract_path = path,
            gasprice=constant.GAS_PRICE,
            timeout=constant.DEFAULT_POLL_TIMEOUT,
        )
        log.info('deploying contract: [{}] ok. address: {} .'.format(contract_name,hexlify(contract_proxy.address)))
        self.local_contract_proxys[contract_name] = contract_proxy
        return contract_proxy

    def transfer_currency(self, sender, to, eth_amount,password=None):
        
        client = self.get_jsonrpc_client_with_sender(sender,password)
        if client == None:
            return

        balance = self.balance(client.sender)

        balance_needed =  eth_amount
        if balance_needed * constant.WEI_TO_ETH > balance:
            print("Not enough balance to fund  accounts with {} eth each. Need {}, have {}".format(
                eth_amount,
                balance_needed,
                balance / constant.WEI_TO_ETH
            ))

        print("Sending {} eth to:".format(eth_amount))
        
        print("  - {}".format(to))
        return client.send_transaction(sender=client.sender, to=to, value=eth_amount * constant.WEI_TO_ETH)

    def estimate_blocktime(self, oldest=256):
        """Calculate a blocktime estimate based on some past blocks.
        Args:
            oldest (int): delta in block numbers to go back.
        Return:
            average block time (int) in seconds
        """
        last_block_number = self.jsonrpc_client_without_sender.block_number()
        # around genesis block there is nothing to estimate
        if last_block_number < 1:
            return 15
        # if there are less than `oldest` blocks available, start at block 1
        if last_block_number < oldest:
            interval = (last_block_number - 1) or 1
        else:
            interval = last_block_number - oldest
        assert interval > 0
        last_timestamp = int(self.jsonrpc_client_without_sender.get_block_header(last_block_number)['timestamp'], 16)
        first_timestamp = int(self.jsonrpc_client_without_sender.get_block_header(last_block_number - interval)['timestamp'], 16)
        delta = last_timestamp - first_timestamp
        return float(delta) / interval

    def block_number(self):
        """ Return the most recent block. """
        return quantity_decoder(self.jsonrpc_client_without_sender.call('eth_blockNumber'))

    def next_block(self):
        target_block_number = self.jsonrpc_client_without_sender.block_number() + 1
        current_block = target_block_number

        while not current_block >= target_block_number:
            current_block = self.jsonrpc_client_without_sender.block_number()
            gevent.sleep(0.5)

        return current_block

    def balance(self, account):
        """ Return the balance of the account of given address. """
        res = self.jsonrpc_client_without_sender.call('eth_getBalance', address_encoder(account), 'latest')
        return quantity_decoder(res)
    
    def nonce(self, account):
        """ Return the nonce of the account of given address. """
        res = self.jsonrpc_client_without_sender.nonce(account)
        return res

    def sendRawTransaction(self, tx_data):
        """ execute offline transaction. """
        result = self.jsonrpc_client_without_sender.call(
                'eth_sendRawTransaction',
                tx_data # data_encoder(tx_data.decode('hex')), # data_encoder(rlp.encode(tx_data)),  #
            )
        return result[2 if result.startswith('0x') else 0:]

class JSONRPCClient(object):
    """ Ethereum JSON RPC client.

    Args:
        host (str): Ethereum node host address.
        port (int): Ethereum node port number.
        privkey (bin): Local user private key, used to sign transactions.
        nonce_update_interval (float): Update the account nonce every
            `nonce_update_interval` seconds.
        nonce_offset (int): Network's default base nonce number.
    """

    def __init__(self, host, port, privkey, nonce_update_interval=5.0, nonce_offset=0):
        endpoint = 'http://{}:{}'.format(host, port)
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_maxsize=50)
        session.mount(endpoint, adapter)

        self.transport = HttpPostClientTransport(
            endpoint,
            post_method=session.post,
            headers={'content-type': 'application/json'},
        )

        self.port = port
        self.privkey = privkey
        self.protocol = JSONRPCProtocol()
        if privkey != '':
            self.sender = privatekey_to_address(privkey)
        else:
            self.sender = ''
        self.nonce_last_update = 0
        self.nonce_current_value = None
        self.nonce_lock = Semaphore()
        self.nonce_update_interval = nonce_update_interval
        self.nonce_offset = nonce_offset

    def __repr__(self):
        return '<JSONRPCClient @%d>' % self.port

    def nonce(self, address):
        if len(address) == 40:
            address = unhexlify(address)

        with self.nonce_lock:
            initialized = self.nonce_current_value is not None
            query_time = now()

            if self.nonce_last_update > query_time:
                # Python's 2.7 time is not monotonic and it's affected by clock
                # resets, force an update.
                self.nonce_update_interval = query_time - self.nonce_update_interval
                needs_update = True
            else:
                last_update_interval = query_time - self.nonce_last_update
                needs_update = last_update_interval > self.nonce_update_interval

            if initialized and not needs_update:
                self.nonce_current_value += 1
                return self.nonce_current_value

            pending_transactions_hex = self.call(
                'eth_getTransactionCount',
                address_encoder(address),
                'pending',
            )
            pending_transactions = quantity_decoder(pending_transactions_hex)
            nonce = pending_transactions + self.nonce_offset

            # we may have hammered the server and not all tx are
            # registered as `pending` yet
            while nonce < self.nonce_current_value:
                log.debug(
                    'nonce on server too low; retrying',
                    server=nonce,
                    local=self.nonce_current_value,
                )

                query_time = now()
                pending_transactions_hex = self.call(
                    'eth_getTransactionCount',
                    address_encoder(address),
                    'pending',
                )
                pending_transactions = quantity_decoder(pending_transactions_hex)
                nonce = pending_transactions + self.nonce_offset

            self.nonce_current_value = nonce
            self.nonce_last_update = query_time
            return self.nonce_current_value

    def gaslimit(self):
        last_block = self.call('eth_getBlockByNumber', 'latest', True)
        gas_limit = quantity_decoder(last_block['gasLimit'])
        return gas_limit

    def new_contract_proxy(self, contract_name,contract_interface, address):
        """ Return a proxy for interacting with a smart contract.

        Args:
            contract_interface: The contract interface as defined by the json.
            address: The contract's address.
        """
        return ContractProxy(
            self,
            self.sender,
            contract_name,
            contract_interface,
            address,
            self.eth_call,
            self.send_transaction,
            self.eth_estimateGas,
        )

    def deploy_solidity_contract(
            self,  # pylint: disable=too-many-locals
            sender,
            contract_name,
            all_contracts,
            libraries,
            constructor_parameters,
            contract_path=None,
            timeout=None,
            gasprice=constant.GAS_PRICE):
        """
        Deploy a solidity contract.
        Args:
            sender (address): the sender address
            contract_name (str): the name of the contract to compile
            all_contracts (dict): the json dictionary containing the result of compiling a file
            libraries (list): A list of libraries to use in deployment
            constructor_parameters (tuple): A tuple of arguments to pass to the constructor
            contract_path (str): If we are dealing with solc >= v0.4.9 then the path
                                 to the contract is a required argument to extract
                                 the contract data from the `all_contracts` dict.
            timeout (int): Amount of time to poll the chain to confirm deployment
            gasprice: The gasprice to provide for the transaction
        """

        if contract_name in all_contracts:
            contract_key = contract_name

        elif contract_path is not None:
            _, filename = os.path.split(contract_path)
            contract_key = filename + ':' + contract_name

            if contract_key not in all_contracts:
                raise ValueError('Unknown contract {}'.format(contract_name))
        else:
            raise ValueError(
                'Unknown contract {} and no contract_path given'.format(contract_name)
            )

        libraries = dict(libraries)
        contract = all_contracts[contract_key]
        contract_interface = contract['abi']
        symbols = solidity_unresolved_symbols(contract['bin_hex'])

        if symbols:
            available_symbols = map(solidity_library_symbol, all_contracts.keys())

            unknown_symbols = set(symbols) - set(available_symbols)
            if unknown_symbols:
                msg = 'Cannot deploy contract, known symbols {}, unresolved symbols {}.'.format(
                    available_symbols,
                    unknown_symbols,
                )
                raise Exception(msg)

            dependencies = deploy_dependencies_symbols(all_contracts)
            deployment_order = dependencies_order_of_build(contract_key, dependencies)

            deployment_order.pop()  # remove `contract_name` from the list

            log.debug('Deploying dependencies: {}'.format(str(deployment_order)))

            for deploy_contract in deployment_order:
                dependency_contract = all_contracts[deploy_contract]

                hex_bytecode = solidity_resolve_symbols(dependency_contract['bin_hex'], libraries)
                bytecode = unhexlify(hex_bytecode)

                dependency_contract['bin_hex'] = hex_bytecode
                dependency_contract['bin'] = bytecode
                transaction_hash_hex = self.send_transaction(
                    sender,
                    to='',
                    data=bytecode,
                    gasprice=gasprice,
                )
                transaction_hash = unhexlify(transaction_hash_hex)

                self.poll(transaction_hash, timeout=timeout)
                receipt = self.eth_getTransactionReceipt(transaction_hash)
                contract_address = receipt['contractAddress']
                # remove the hexadecimal prefix 0x from the address
                contract_address = contract_address[2:]

                libraries[deploy_contract] = contract_address

                deployed_code = self.eth_getCode(unhexlify(contract_address))

                if deployed_code == '0x':
                    raise RuntimeError('Contract address has no code, check gas usage.')

            hex_bytecode = solidity_resolve_symbols(contract['bin_hex'], libraries)
            bytecode = unhexlify(hex_bytecode)

            contract['bin_hex'] = hex_bytecode
            contract['bin'] = bytecode
        if constructor_parameters:
            translator = ContractTranslator(contract_interface)
            parameters = translator.encode_constructor_arguments(constructor_parameters)
            bytecode = contract['bin'] + parameters
        else:
            bytecode = contract['bin']
        transaction_hash_hex = self.send_transaction(
            sender,
            to='',
            data=bytecode,
            gasprice=gasprice,
        )
        transaction_hash = unhexlify(transaction_hash_hex)
        self.poll(transaction_hash, timeout=timeout)
        receipt = self.eth_getTransactionReceipt(transaction_hash)
        contract_address = receipt['contractAddress']

        deployed_code = self.eth_getCode(unhexlify(contract_address[2:]))

        if deployed_code == '0x':
            raise RuntimeError(
                'Deployment of {} failed. Contract address has no code, check gas usage.'.format(
                    contract_name,
                )
            )

        return self.new_contract_proxy(
            contract_name,
            contract_interface,
            contract_address,
        )

    def new_filter(self, address=None, topics=None, fromBlock=0, toBlock='latest'):
        """ Creates a filter object, based on filter options, to notify when
        the state changes (logs). To check if the state has changed, call
        eth_getFilterChanges.
        """
        if isinstance(fromBlock, int):
            fromBlock = hex(fromBlock)

        if isinstance(toBlock, int):
            toBlock = hex(toBlock)

        json_data = {
            'fromBlock': fromBlock or hex(0),
            'toBlock': toBlock or 'latest',
        }
        if address is not None:
            json_data['address'] = address_encoder(normalize_address(address))

        if topics is not None:
            if not isinstance(topics, list):
                raise ValueError('topics must be a list')
            json_data['topics'] = [topic_encoder(topic) for topic in topics]
        
        #filter_id = self.call('eth_newFilter', json_data)
        #return quantity_decoder(filter_id)
        return json_data


    def filter_changes(self, json_data):
        #changes = self.call('eth_getFilterChanges', quantity_encoder(fid))

        changes = self.call('eth_getLogs', json_data)

        if not changes:
            return list()

        if isinstance(changes, bytes):
            return data_decoder(changes)

        decoders = {
            'blockHash': data_decoder,
            'transactionHash': data_decoder,
            'data': data_decoder,
            'address': address_decoder,
            'topics': lambda x: [topic_decoder(t) for t in x],
            'blockNumber': quantity_decoder,
            'logIndex': quantity_decoder,
            'transactionIndex': quantity_decoder,
        }

        return [
            {k: decoders[k](v) for k, v in c.items() if v is not None and k in decoders.keys()}
            for c in changes
        ]

    def poll_contract_events(
        self,
        contract_address,
        translator,
        fromBlock,
        condition=None,
        wait=constant.DEFAULT_RETRY_INTERVAL, timeout=constant.DEFAULT_TIMEOUT):
        
        result = list()
        json_data = self.new_filter(contract_address,fromBlock=fromBlock)
        for i in range(0, timeout + wait, wait):
            events = self.filter_changes(json_data)
            log.debug('waiting for transaction events...{}s\r'.format(i))
            if events:                
                for match_log in events:
                    decoded_event = translator.decode_event(
                        match_log['topics'],
                        match_log['data'],
                    )
                    if decoded_event is not None:
                        decoded_event['block_number'] = match_log.get('blockNumber')
                        decoded_event['transaction_hash'] = data_encoder(match_log.get('transactionHash'))
                        if not condition or condition(decoded_event):
                            result.append(decoded_event)
                if result !=[]:
                    return result 
            if i < timeout:
                gevent.sleep(wait)
        return list()

    @check_node_connection
    def call(self, method, *args):
        """ Do the request and return the result.

        Args:
            method (str): The RPC method.
            args: The encoded arguments expected by the method.
                - Object arguments must be supplied as a dictionary.
                - Quantity arguments must be hex encoded starting with '0x' and
                without left zeros.
                - Data arguments must be hex encoded starting with '0x'
        """
        request = self.protocol.create_request(method, args)
        log.debug("\nRPC Request: {}".format(request.serialize()))
        reply = self.transport.send_message(request.serialize())

        jsonrpc_reply = self.protocol.parse_reply(reply)
        if isinstance(jsonrpc_reply, JSONRPCSuccessResponse):
            return jsonrpc_reply.result
        elif isinstance(jsonrpc_reply, JSONRPCErrorResponse):
            raise EthNodeCommunicationError(jsonrpc_reply.error)
        else:
            raise EthNodeCommunicationError('Unknown type of JSONRPC reply')

    def send_transaction(
            self,
            sender,
            to,
            value=0,
            data='',
            startgas=0,
            gasprice=constant.GAS_PRICE,
            nonce=None):
        """ Helper to send signed messages.

        This method will use the `privkey` provided in the constructor to
        locally sign the transaction. This requires an extended server
        implementation that accepts the variables v, r, and s.
        """
        if not self.privkey and not sender:
            raise ValueError('Either privkey or sender needs to be supplied.')

        if self.privkey:
            privkey_address = privatekey_to_address(self.privkey)
            sender = sender or privkey_address

            if sender != privkey_address:
                print('sender {} != privkey_address {}'.format(hexlify(sender),hexlify(privkey_address)))
                raise ValueError('sender for a different privkey .')

            if nonce is None:
                nonce = self.nonce(sender)
        else:
            if nonce is None:
                nonce = 0

        if not startgas:
            startgas = self.gaslimit() / 3

        tx = Transaction(nonce, gasprice, startgas, to=to, value=value, data=data)
        if self.privkey:
            tx.sign(self.privkey)
            result = self.call(
                'eth_sendRawTransaction',
                data_encoder(rlp.encode(tx)),
            )
            return result[2 if result.startswith('0x') else 0:]

        else:

            # rename the fields to match the eth_sendTransaction signature
            tx_dict = tx.to_dict()
            tx_dict.pop('hash')
            tx_dict['sender'] = sender
            tx_dict['gasPrice'] = tx_dict.pop('gasprice')
            tx_dict['gas'] = tx_dict.pop('startgas')
            res = self.eth_sendTransaction(**tx_dict)

        assert len(res) in (20, 32)
        return hexlify(res)

    def eth_sendTransaction(
            self,
            nonce=None,
            sender='',
            to='',
            value=0,
            data='',
            gasPrice=constant.GAS_PRICE,
            gas=constant.GAS_PRICE):
        """ Creates new message call transaction or a contract creation, if the
        data field contains code.

        Args:
            sender (address): The 20 bytes address the transaction is sent from.
            to (address): DATA, 20 Bytes - (optional when creating new
                contract) The address the transaction is directed to.
            gas (int): Gas provided for the transaction execution. It will
                return unused gas.
            gasPrice (int): gasPrice used for each unit of gas paid.
            value (int): Value sent with this transaction.
            data (bin): The compiled code of a contract OR the hash of the
                invoked method signature and encoded parameters.
            nonce (int): This allows to overwrite your own pending transactions
                that use the same nonce.
        """

        if to == '' and data.isalnum():
            warnings.warn(
                'Verify that the data parameter is _not_ hex encoded, if this is the case '
                'the data will be double encoded and result in unexpected '
                'behavior.'
            )

        if to == '0' * 40:
            warnings.warn('For contract creation the empty string must be used.')

        if sender is None:
            raise ValueError('sender needs to be provided.')

        json_data = {
            'to': data_encoder(normalize_address(to, allow_blank=True)),
            'value': quantity_encoder(value),
            'gasPrice': quantity_encoder(gasPrice),
            'gas': quantity_encoder(gas),
            'data': data_encoder(data),
            'from': address_encoder(sender),
        }

        if nonce is not None:
            json_data['nonce'] = quantity_encoder(nonce)

        res = self.call('eth_sendTransaction', json_data)

        return data_decoder(res)

    def _format_call(self, sender='', to='', value=0, data='',
                     startgas=constant.GAS_PRICE, gasprice=constant.GAS_PRICE):
        """ Helper to format the transaction data. """

        json_data = dict()

        if sender is not None and sender!='' and sender!='0x':
            json_data['from'] = address_encoder(sender)

        if to is not None:
            json_data['to'] = data_encoder(to)

        if value is not None:
            json_data['value'] = quantity_encoder(value)

        if gasprice is not None:
            json_data['gasPrice'] = quantity_encoder(gasprice)

        if startgas is not None:
            json_data['gas'] = quantity_encoder(startgas)

        if data is not None:
            json_data['data'] = data_encoder(data)

        return json_data

    def eth_call(
            self,
            sender='',
            to='',
            value=0,
            data='',
            startgas=constant.GAS_PRICE,
            gasprice=constant.GAS_PRICE,
            block_number='latest'):
        """ Executes a new message call immediately without creating a
        transaction on the blockchain.

        Args:
            sender: The address the transaction is sent from.
            to: The address the transaction is directed to.
            gas (int): Gas provided for the transaction execution. eth_call
                consumes zero gas, but this parameter may be needed by some
                executions.
            gasPrice (int): gasPrice used for unit of gas paid.
            value (int): Integer of the value sent with this transaction.
            data (bin): Hash of the method signature and encoded parameters.
                For details see Ethereum Contract ABI.
            block_number: Determines the state of ethereum used in the
                call.
        """

        json_data = self._format_call(
            sender,
            to,
            value,
            data,
            startgas,
            gasprice,
        )
        res = self.call('eth_call', json_data, block_number)

        return data_decoder(res)

    def eth_estimateGas(
            self,
            sender='',
            to='',
            value=0,
            data='',
            startgas=constant.GAS_PRICE,
            gasprice=constant.GAS_PRICE):
        """ Makes a call or transaction, which won't be added to the blockchain
        and returns the used gas, which can be used for estimating the used
        gas.

        Args:
            sender: The address the transaction is sent from.
            to: The address the transaction is directed to.
            gas (int): Gas provided for the transaction execution. eth_call
                consumes zero gas, but this parameter may be needed by some
                executions.
            gasPrice (int): gasPrice used for unit of gas paid.
            value (int): Integer of the value sent with this transaction.
            data (bin): Hash of the method signature and encoded parameters.
                For details see Ethereum Contract ABI.
            block_number: Determines the state of ethereum used in the
                call.
        """

        json_data = self._format_call(
            sender,
            to,
            value,
            data,
            startgas,
            gasprice,
        )
        res = self.call('eth_estimateGas', json_data)

        return quantity_decoder(res)

    def eth_getTransactionReceipt(self, transaction_hash):
        """ Returns the receipt of a transaction by transaction hash.

        Args:
            transaction_hash: Hash of a transaction.

        Returns:
            A dict representing the transaction receipt object, or null when no
            receipt was found.
        """
        if transaction_hash.startswith('0x'):
            warnings.warn(
                'transaction_hash seems to be already encoded, this will'
                ' result in unexpected behavior'
            )

        if len(transaction_hash) != 32:
            raise ValueError(
                'transaction_hash length must be 32 (it might be hex encoded)'
            )

        transaction_hash = data_encoder(transaction_hash)
        return self.call('eth_getTransactionReceipt', transaction_hash)

    def eth_getCode(self, address, block='latest'):
        """ Returns code at a given address.

        Args:
            address: An address.
            block: Integer block number, or the string 'latest',
                'earliest' or 'pending'.
        """
        if address.startswith('0x'):
            warnings.warn(
                'address seems to be already encoded, this will result '
                'in unexpected behavior'
            )

        if len(address) != 20:
            raise ValueError(
                'address length must be 20 (it might be hex encoded)'
            )

        return self.call(
            'eth_getCode',
            address_encoder(address),
            block,
        )

    def eth_getTransactionByHash(self, transaction_hash):
        """ Returns the information about a transaction requested by
        transaction hash.
        """

        if transaction_hash.startswith('0x'):
            warnings.warn(
                'transaction_hash seems to be already encoded, this will'
                ' result in unexpected behavior'
            )

        if len(transaction_hash) != 32:
            raise ValueError(
                'transaction_hash length must be 32 (it might be hex encoded)'
            )

        transaction_hash = data_encoder(transaction_hash)
        return self.call('eth_getTransactionByHash', transaction_hash)

    def poll(self, transaction_hash, confirmations=None, timeout=None):
        """ Wait until the `transaction_hash` is applied or rejected.
        If timeout is None, this could wait indefinitely!

        Args:
            transaction_hash (hash): Transaction hash that we are waiting for.
            confirmations (int): Number of block confirmations that we will
                wait for.
            timeout (float): Timeout in seconds, raise an Excpetion on
                timeout.
        """
        if transaction_hash.startswith('0x'):
            warnings.warn(
                'transaction_hash seems to be already encoded, this will'
                ' result in unexpected behavior'
            )

        if len(transaction_hash) != 32:
            raise ValueError(
                'transaction_hash length must be 32 (it might be hex encoded)'
            )

        transaction_hash = data_encoder(transaction_hash)

        deadline = None
        if timeout:
            deadline = gevent.Timeout(timeout)
            deadline.start()

        try:
            # used to check if the transaction was removed, this could happen
            # if gas price is too low:
            #
            # > Transaction (acbca3d6) below gas price (tx=1 Wei ask=18
            # > Shannon). All sequential txs from this address(7d0eae79)
            # > will be ignored
            #
            last_result = None
            count = 0
            print '\n'
            while True:
                # Could return None for a short period of time, until the
                # transaction is added to the pool
                transaction = self.call('eth_getTransactionByHash', transaction_hash)
                """
                # if the transaction was added to the pool and then removed
                if transaction is None and last_result is not None:
                    raise Exception('invalid transaction, check gas price')
                """
                # the transaction was added to the pool and mined
                if transaction and transaction['blockNumber'] is not None:
                    break

                last_result = transaction
                
                print 'waiting for transaction %s to be mined... %3ds\r' % (transaction_hash,count),
                sys.stdout.flush()
                count = count+1
                gevent.sleep(1)
            print '\nto be mined ok.\n'
            if confirmations:
                # this will wait for both APPLIED and REVERTED transactions
                transaction_block = quantity_decoder(transaction['blockNumber'])
                confirmation_block = transaction_block + confirmations

                block_number = self.block_number()
                print '\n'
                while block_number < confirmation_block:
                    print 'waiting for transaction %s confirm... %d/%d \r' % (transaction_hash,block_number+confirmations-confirmation_block,confirmations),
                    sys.stdout.flush()
                    gevent.sleep(1)
                    block_number = self.block_number()
                print '\n'

        except gevent.Timeout:
            raise Exception('timeout when polling for transaction')

        finally:
            if deadline:
                deadline.cancel()

class JSONRPCClient_for_infura(JSONRPCClient):
    def __init__(self, endpoint, privkey, nonce_update_interval=5.0, nonce_offset=0):
        
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_maxsize=50)
        session.mount(endpoint, adapter)

        self.endpoint = endpoint
        self.transport = None
        self.protocol = None

        self.privkey = privkey
        
        if privkey != '':
            self.sender = privatekey_to_address(privkey)
            #print('temp: sender={}'.format(hexlify(self.sender)))
        else:
            self.sender = ''
        self.nonce_last_update = 0
        self.nonce_current_value = None
        self.nonce_lock = Semaphore()
        self.nonce_update_interval = nonce_update_interval
        self.nonce_offset = nonce_offset

    @check_node_connection
    def call(self, method, *args):
        
        payload = {
            "jsonrpc": "2.0",
            "id": 29846618,
            "method": method,
        }
        if isinstance(args, tuple):
            payload['params'] = args
        else:
            payload['params'] = [args,]
        resp = requests.post(self.endpoint, data=json.dumps(payload))
        result = json.loads(resp.text)
        if 'result' in result.keys():
            #print("POST \nmethod:{} \nresult:{} ".format(payload['method'],result['result']))
            return result['result']
        else:
            #print("POST \nmethod:{} \nerror:{} ".format(payload['method'],result['error']))
            return None
