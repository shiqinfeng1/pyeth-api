# -*- coding: utf-8 -*-
from __future__ import print_function
import click
import cStringIO
import json
import sys
import time
from logging import StreamHandler, Formatter
from flask.json import jsonify
import gevent
from gevent.event import Event
import IPython
from IPython.lib.inputhook import inputhook_manager
from devp2p.service import BaseService
from ethereum.slogging import getLogger
from ethereum._solidity import compile_file
from ethereum.utils import denoms
from pyethapp.utils import bcolors as bc
from pyethapp.jsonrpc import default_gasprice
from pyethapp.console_service import GeventInputHook, SigINTHandler
from api.python import PYETHAPI
from service.utils import  get_contract_path, safe_address_decode,privatekey_to_address
from binascii import hexlify, unhexlify

# ipython needs to accept "--gui gevent" option
IPython.core.shellapp.InteractiveShellApp.gui.values += ('gevent',)
inputhook_manager.register('gevent')(GeventInputHook)


def ATMChain_print_usage():
    print("\t{}use `{}account{}` to interact with the account manager.".format(
        bc.OKBLUE, bc.HEADER, bc.OKBLUE))
    print("\tuse `{}chain{}` to interact with the blockchain.".format(bc.HEADER, bc.OKBLUE))
    print("\tuse `{}help(<topic>){}` for help on a specific topic.".format(bc.HEADER, bc.OKBLUE))
    print("\ttype `{}usage(){}` to see this help again.".format(bc.HEADER, bc.OKBLUE))
    print("\n" + bc.ENDC)

class ATMChainTools(object):
    def __init__(self, pyeth_api):
        self.pyeth_api = pyeth_api
        
    def _print_proxy_info(self,proxy):
        print("=======================================")
        print("{:20}: {}".format('chain_name',proxy.chain_name))
        if proxy.endpoint !=None:
            print("{:20}: {}".format('endpoint',proxy.endpoint))
        else:
            print("{:20}: {}".format('host',proxy.host))
            print("{:20}: {}".format('port',proxy.port))
        print("{:20}: {}".format('keystore_path',proxy.account_manager.keystore_path))
        print("{:20}: {}".format('default accounts',list(proxy.account_manager.accounts.keys())))

    def new_blockchain_proxy(self, chain_name,host,port,infura_endpoint=None):
        proxy = self.pyeth_api.new_blockchain_proxy(chain_name,host,port,infura_endpoint)
        self._print_proxy_info(proxy)

    def blockchain_proxy_list(self):
        for k in self.pyeth_api.blockchain_proxy_list():
            v=self.pyeth_api._get_chain_proxy(k)
            self._print_proxy_info(v)

    def query_eth_balance(self,chain_name,account):
        result = self.pyeth_api.query_eth_balance(chain_name,account)
        print('------------------------------------')
        print('{:<30}: {:,}'.format(account, result))

    def deploy_ATM_contract(self,atm_address=None):
        self.pyeth_api.deploy_ATM_contract(atm_address)

    def new_account(self,chain_name, key=None):
        assert isinstance(key,str) and len(key)==64

        password = click.prompt('Password to encrypt private key', default='', hide_input=True,
                                confirmation_prompt=False, show_default=False)
        self.pyeth_api.new_account(chain_name, password, key)

    def check_account(self,privkey):
        assert isinstance(privkey,str)
        privkey = unhexlify(privkey)
        address = privatekey_to_address(privkey)
        print('{}: {}'.format(hexlify(privkey),hexlify(address)))

    def eth_accounts_list(self,chain_name):
        acc = self.pyeth_api.eth_accounts_list(chain_name)
        print('------------------------------------\n[ethereum user accounts]:')
        for k, v in enumerate(acc):
            print('{}: {}'.format(k,'0x'+v))
        print('------------------------------------')

    def ATM_accounts_list(self): 
        a0,a1,a2 = self.pyeth_api.ATM_accounts_list()
        print('------------------------------------\n[contract addresses]:')
        for k, v in a0.iteritems():
            print('{}: {}'.format(k,v))
            print('|--owner: {}'.format(self.pyeth_api.adminAddress))
        print('------------------------------------\n[ethereum user accounts]:')
        for k, v in enumerate(a1):
            print('{}: {}'.format(k,'0x'+v))
        print('------------------------------------\n[quorum user accounts]:')
        for k, v in enumerate(a2):
            print('{}: {}'.format(k,'0x'+v))

    def query_atmchain_balance(self,account):
        result = self.pyeth_api.query_atmchain_balance('ethereum','quorum',account)
        print('------------------------------------')
        for key in sorted(result.keys()):
            print('{:<30}: {:,}'.format(key, result[key]))

    def lock_ATM(self,adviser,lock_amount):
        self.pyeth_api.lock_ATM('ethereum','quorum',adviser,lock_amount)

    def settle_ATM(self,scaner,settle_amount):
        self.pyeth_api.settle_ATM('ethereum','quorum',scaner,settle_amount)

    def transfer_ATM(self,chain_name,sender,to,amount):
        if chain_name == 'quorum':
            self.pyeth_api.transfer_ATM(chain_name,'ERC223Token',sender,to,amount,True)
        elif chain_name == 'ethereum':
            self.pyeth_api.transfer_ATM(chain_name,'ERC20Token',sender,to,amount)
        else:
            print('unkonw chain name: {}'.format(chain_name))
            return

class AppTools(object):
    def __init__(self, chain):
        self.chain = chain
        self.current_sender = None

    def switch_sender(self,address): 
        assert isinstance(address,str) 
        """
        if address[:2] == '0x':
            address = address[2:]
        assert len(address) == 40
        """
        self.current_sender = address
        print('current_sender: {}'.format(self.current_sender))

    def deploy_twitter_rewards_contract(self,chain_name): 
        _proxy = self.chain.pyeth_api._get_chain_proxy(chain_name)
        if self.current_sender == None:
            self.current_sender = _proxy.account_manager.admin_account 
        self.chain.pyeth_api.deploy_twitter_rewards_contract(self.current_sender,chain_name)

    def bind_account(self,chain_name, user_id, user_addr,contract_address=None):
        _proxy = self.chain.pyeth_api._get_chain_proxy(chain_name)
        if self.current_sender == None:
            self.current_sender = _proxy.account_manager.admin_account 
        self.chain.pyeth_api.bind_account(self.current_sender,chain_name,user_id, user_addr,contract_address)

    def unbind_account(self,chain_name, user_id,contract_address=None): 
        _proxy = self.chain.pyeth_api._get_chain_proxy(chain_name)
        if self.current_sender == None:
            self.current_sender = _proxy.account_manager.admin_account
        self.chain.pyeth_api.unbind_account(self.current_sender,chain_name,user_id,contract_address)
    
    def twitter_status_list(self): 
        self.chain.pyeth_api.twitter_status_list()

    def retwitter_list(self,status_id): 
        self.chain.pyeth_api.retwitter_list(status_id)
    
    def get_luckyboys(self,chain_name,status_id,luckyboys_num,contract_address=None):
        _proxy = self.chain.pyeth_api._get_chain_proxy(chain_name)
        if self.current_sender == None:
            self.current_sender = _proxy.account_manager.admin_account
        self.chain.pyeth_api.get_luckyboys(self.current_sender,chain_name,status_id,luckyboys_num,contract_address)

class Console(object):

    """A service starting an interactive ipython session when receiving the
    SIGSTP signal (e.g. via keyboard shortcut CTRL-Z).
    """

    name = 'console'

    def __init__(self, pyeth_api):
        self.pyeth_api = pyeth_api
        self.interrupt = Event()
        self.console_locals = {}
        self.start()
        self.interrupt.set()

    def start(self):
        # start console service
        ATMChain_tools=ATMChainTools(self.pyeth_api)
        App_tools=AppTools(ATMChain_tools)
        self.console_locals  = dict(
            chain=ATMChain_tools,
            app_twitter=App_tools,
            ATMChainUsage=ATMChain_print_usage,
        )

    def run(self):
        self.interrupt.wait()
        print('\n' * 2)
        print("Entering Console" + bc.OKGREEN)
        print("Tip:" + bc.OKBLUE)
        ATMChain_print_usage()

        # Remove handlers that log to stderr
        root = getLogger()
        """
        for handler in root.handlers[:]:
            if isinstance(handler, StreamHandler) and handler.stream == sys.stderr:
                root.removeHandler(handler)
        """
        stream = cStringIO.StringIO()
        handler = StreamHandler(stream=stream)
        handler.formatter = Formatter("%(levelname)s:%(name)s %(message)s") # 实例化formatter
        root.addHandler(handler) # 为logger添加handler  

        def lastlog(n=30, prefix=None, level=None):
            """Print the last `n` log lines to stdout.
            Use `prefix='p2p'` to filter for a specific logger.
            Use `level=INFO` to filter for a specific level.
            Level- and prefix-filtering are applied before tailing the log.
            """
            lines = (stream.getvalue().strip().split('\n') or [])
            if prefix:
                lines = [
                    line
                    for line in lines
                    if line.split(':')[1].startswith(prefix)
                ]
            if level:
                lines = [
                    line
                    for line in lines
                    if line.split(':')[0] == level
                ]
            for line in lines[-n:]:
                print(line)

        self.console_locals['lastlog'] = lastlog

        err = cStringIO.StringIO()
        sys.stderr = err

        def lasterr(n=1):
            """Print the last `n` entries of stderr to stdout.
            """
            for line in (err.getvalue().strip().split('\n') or [])[-n:]:
                print(line)

        self.console_locals['lasterr'] = lasterr

        IPython.start_ipython(argv=['--gui', 'gevent'], user_ns=self.console_locals)
        self.interrupt.clear()

        sys.exit(0)
