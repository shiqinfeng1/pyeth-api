# -*- coding: utf-8 -*-
from __future__ import print_function
import click
import cStringIO
import json
import sys,os
import time
from logging import StreamHandler, Formatter
from flask.json import jsonify
import gevent
from gevent.event import Event
import IPython
from IPython.lib.inputhook import inputhook_manager
from devp2p.service import BaseService
from ethereum import slogging
from ethereum.utils import denoms
from pyethapp.utils import bcolors as bc
from pyethapp.jsonrpc import default_gasprice
from pyethapp.console_service import GeventInputHook, SigINTHandler
from api.python import PYETHAPI
from service.utils import  get_contract_path, safe_address_decode,privatekey_to_address
from binascii import hexlify, unhexlify
from service.utils import (
    split_endpoint
)
from service import constant
import custom.custom_contract_events as custom_contract_events
# ipython needs to accept "--gui gevent" option
IPython.core.shellapp.InteractiveShellApp.gui.values += ('gevent',)
inputhook_manager.register('gevent')(GeventInputHook)


def ATMChain_print_usage():
    print("\tuse `{}chain{}` to interact with the blockchain.".format(bc.HEADER, bc.OKBLUE))
    print("\ttype `{}usage(){}` to see this help again.".format(bc.HEADER, bc.OKBLUE))
    print("\n" + bc.ENDC)

class ATMChainTools(object):
    def __init__(self, pyeth_api):
        self.pyeth_api = pyeth_api

    def set_log_level(self,level):
        if level not in ('critical','error','warn','warning','info','debug','notest'):
            print("level not in ('critical','error','warn','warning','info','debug','notest')")
            return
        self.pyeth_api.set_log_level(level.upper())
        
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

    def new_blockchain_proxy(self, chain_name,endpoint,keystore_path=None,admin_account=None):
        if keystore_path != None:
            keystore_path = os.path.abspath(keystore_path)
        else: 
            keystore_path = os.getcwd()+'/'+sys.argv[0]+'/keystore'
        proxy = self.pyeth_api.new_blockchain_proxy(chain_name,endpoint,keystore_path,admin_account)
        self._print_proxy_info(proxy)

    def blockchain_proxy_list(self):
        for k in self.pyeth_api.blockchain_proxy_list():
            v=self.pyeth_api._get_chain_proxy(k)
            self._print_proxy_info(v)

    def query_currency_balance(self,chain_name,account):
        result = self.pyeth_api.query_currency_balance(chain_name,account)
        result = float(result)/constant.WEI_TO_ETH
        print('------------------------------------')
        print('{:<30}: {:,}'.format(account, result))
        return result

    def query_token_balance(self,chain_name,account):
        _proxy = self.pyeth_api._get_chain_proxy(chain_name)

        ERC20Token_ethereum = _proxy.attach_contract(
                    'ATMToken',
                    contract_file=custom_contract_events.__contractInfo__['ATMToken']['file'], 
                    contract_address=unhexlify(custom_contract_events.__contractInfo__['ATMToken']['address']),)

        return ERC20Token_ethereum.balanceOf(account) if ERC20Token_ethereum != None else 0
  

    def query_atmchain_balance(self,account):
        result = self.pyeth_api.query_atmchain_balance('ethereum','atmchain',account)
        res = dict()

        res['ETH balance'] = float(result['ETH_balance'])/constant.WEI_TO_ETH

        res['ATM balance in ethereum({})'.format(custom_contract_events.__contractInfo__['ATMToken']['address'])] = float(result['ATM_balance_ethereum'])/constant.ATM_DECIMALS 
    
        res['ATM balance in atmchain'] = float(result['ATM_balance_atmchain'])/constant.WEI_TO_ETH

        print('------------------------------------')
        for key in sorted(res.keys()):
            print('{:<30}: {:,}'.format(key, res[key]))

    def new_account(self,chain_name, key=None):
        assert isinstance(key,str) and len(key)==64

        password = click.prompt('Password to encrypt private key', default='', hide_input=True,
                                confirmation_prompt=False, show_default=False)
        self.pyeth_api.new_account(chain_name, password, key)

    def set_admin_account(self,chain_name,old_admin_address,new_admin_address):
        self.pyeth_api.set_admin_account(chain_name,old_admin_address,new_admin_address)

    def check_account(self,privkey):
        assert isinstance(privkey,str)
        privkey = unhexlify(privkey)
        address = privatekey_to_address(privkey)
        print('{}: {}'.format(hexlify(privkey),hexlify(address)))
    
    def accounts_list(self,chain_name):
        acc = self.pyeth_api.eth_accounts_list(chain_name)
        print('------------------------------------\n[ethereum user accounts]:')
        for k, v in enumerate(acc):
            print('{}: {}'.format(k,'0x'+v))
        print('------------------------------------')
    """
    def ATM_accounts_list(self): 
        a0,a1,a2 = self.pyeth_api.ATM_accounts_list()
        print('------------------------------------\n[contract addresses]:')
        for k, v in a0.iteritems():
            print('{}: {}'.format(k,v))
        print('------------------------------------\n[ethereum user accounts]:')
        for k, v in enumerate(a1):
            print('{}: {}'.format(k,'0x'+v))
        print('------------------------------------\n[atmchain user accounts]:')
        for k, v in enumerate(a2):
            print('{}: {}'.format(k,'0x'+v))

    def lock_ATM(self,adviser,lock_amount):
        self.pyeth_api.lock_ATM('ethereum','atmchain',adviser,lock_amount)

    def settle_ATM(self,scaner,settle_amount):
        self.pyeth_api.settle_ATM('ethereum','atmchain',scaner,settle_amount)
    """
    def ethereum_transfer_eth(self,sender,to,amount):
        print("\n***unit of measurement is WEI(10^18) ***\n")
        self.pyeth_api.transfer_currency("ethereum",sender,to,amount)

    def atmchain_transfer_atm(self,sender,to,amount):
        print("\n***unit of measurement is WEI(10^18) ***\n")
        self.pyeth_api.transfer_currency("atmchain",sender,to,amount)

    def ethereum_transfer_ATM(self,sender,to,amount):
        print("\n***unit of measurement is 10^8 ***\n")
        contract_address = custom_contract_events.__contractInfo__['ATMToken']['address']
        if contract_address == "" or len(contract_address)!=40:
            print("invalid ATM token address:{}".format(contract_address))
            return
        self.pyeth_api.transfer_token("ethereum",contract_address,sender,to,amount,False)

    def deposit(self,user,amount):
        balance = self.query_token_balance('ethereum',user)
        if balance < amount:
            print("user {} in ethereum has insufficient balance: {}. need: {}".format(user,balance,amount))
            return
        self.ethereum_transfer_ATM(user,custom_contract_events.__contractInfo__['HomeBridge']['address'],amount)

    def withdraw(self,user,amount):
        balance = self.pyeth_api.query_currency_balance('atmchain',user)
        if int(balance) < amount:
            print("user {} in atmchain has insufficient balance: {}. need: {}".format(user,balance,amount))
            return
        self.atmchain_transfer_atm(user,custom_contract_events.__contractInfo__['ForeignBridge']['address'],amount)

    def send_raw_transaction(self,chain_name,signed_data):
        self.pyeth_api.send_raw_transaction(chain_name,signed_data)

    def deposit_atm_manual(self,id):
        self.pyeth_api.deposit_atm_manual(id)

    def query_deposit_progress(self,user=None,tx_hash=None):
        result = self.pyeth_api.query_deposit_progress(user,tx_hash)
        for record in result:
            print(record)

class AppTwitterTools(object):
    def __init__(self, chain):
        self.chain = chain
        self.current_sender = None

    def switch_sender(self,address): 
        assert isinstance(address,str) 
        assert address[:2] == '0x'
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
    
    def query_bindinfo(self,chain_name, screen_name,contract_address=None): 
        _proxy = self.chain.pyeth_api._get_chain_proxy(chain_name)
        if self.current_sender == None:
            self.current_sender = _proxy.account_manager.admin_account
        self.chain.pyeth_api.query_bindinfo(self.current_sender,chain_name,screen_name,contract_address)

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
        App_twitter_tools=AppTwitterTools(ATMChain_tools)
        self.console_locals  = dict(
            chain=ATMChain_tools,
            app_twitter=App_twitter_tools,
            usage=ATMChain_print_usage,
        )

    def run(self):
        self.interrupt.wait()
        print('\n' * 2)
        print("Entering Console" + bc.OKGREEN)
        print("Tip:" + bc.OKBLUE)
        ATMChain_print_usage()

        # Remove handlers that log to stderr
        root = slogging.get_logger("root")
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
