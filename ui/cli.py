# -*- coding: utf-8 -*-
import click
import os
import sys
import gevent
import gevent.monkey
import signal
from gevent import Greenlet
from service import constant 
from service.utils import (
    split_endpoint
)
from binascii import hexlify, unhexlify
from api.rest import APIServer, RestAPI
from ethereum import slogging
from api.python import PYETHAPI_ATMCHAIN
from applications.twitter_rewards_plan.twitter_rewards_plan import PYETHAPI_ATMCHAIN_REWARDS_PLAN
from ui.console import Console
import custom.custom_contract_events as custom_contract_events

pyethapi = dict()
pyethapi['atmchain'] = PYETHAPI_ATMCHAIN
pyethapi['atmchain_rewards_plan'] = PYETHAPI_ATMCHAIN_REWARDS_PLAN

def toogle_cpu_profiler(atmchain):
    try:
        from atmchain.utils.profiling.cpu import CpuProfiler
    except ImportError:
        slogging.get_logger(__name__).exception('cannot start cpu profiler')
        return

    if hasattr(atmchain, 'profiler') and isinstance(atmchain.profiler, CpuProfiler):
        atmchain.profiler.stop()
        atmchain.profiler = None

    elif not hasattr(atmchain, 'profiler') and atmchain.config['database_path'] != ':memory:':
        atmchain.profiler = CpuProfiler(atmchain.config['database_path'])
        atmchain.profiler.start()


def toggle_trace_profiler(atmchain):
    try:
        from atmchain.utils.profiling.trace import TraceProfiler
    except ImportError:
        slogging.get_logger(__name__).exception('cannot start tracer profiler')
        return

    if hasattr(atmchain, 'profiler') and isinstance(atmchain.profiler, TraceProfiler):
        atmchain.profiler.stop()
        atmchain.profiler = None

    elif not hasattr(atmchain, 'profiler') and atmchain.config['database_path'] != ':memory:':
        atmchain.profiler = TraceProfiler(atmchain.config['database_path'])
        atmchain.profiler.start()



OPTIONS = [
    click.option(
        '--gas-price',
        help="Set the Ethereum transaction's gas price",
        default=constant.GAS_PRICE,
        type=int,
        show_default=True,
    ),
    click.option(
        '--rpcaddress',
        help='"host:port" for the service to listen on.',
        default='0.0.0.0:{}'.format(constant.INITIAL_PORT),
        type=str,
        show_default=True,
    ),
    click.option(
        '--rpccorsdomain',
        help='Comma separated list of domains to accept cross origin requests.',
        default='http://localhost:*/*',
        type=str,
        show_default=True,
    ),

    click.option(
        '--console',
        help='Start the interactive console',
        is_flag=True
    ),
    click.option(
        '--rpc',
        help=(
            'Start with or without the RPC server.'
        ),
        default=True,
        show_default=True,
    ),
    click.option(
        '--inst',
        help=(
            'Start with specified business.'
        ),
        default='atmchain', #atmchain_rewards_plan
        type=str,
        show_default=True,
    ),
    click.option(
        '--admin',
        help=(
            'admin account of chain.'
        ),
        default=None,
        type=str,
        show_default=True,
    ),
    click.option(
        '--password',
        help=(
            'password of admin account.'
        ),
        default=None,
        type=str,
        show_default=True,
    ),
]

def options(func):
    """Having the common app options as a decorator facilitates reuse.
    """
    for option in OPTIONS:
        func = option(func)
    return func

@options
@click.command()
def app(gas_price,
        rpccorsdomain,
        rpcaddress,
        rpc,
        console,
        inst,
        admin,
        password):

    # pylint: disable=too-many-locals,too-many-branches,too-many-statements,unused-argument

    from service.blockchain import BlockChainService

    blockchain_service = BlockChainService()

    return blockchain_service

def  _get_pyeth_api(inst,blockchain_proxy):
    if inst in pyethapi.keys():
        pyeth_api = pyethapi[inst](blockchain_proxy)
    else:
        pyeth_api = pyethapi['atmchain'](blockchain_proxy)
    return pyeth_api

@click.group(invoke_without_command=True)
@options
@click.pass_context
def run(ctx, **kwargs):
    
    server1 = None
    server2 = None
    pyeth_api = None
    if ctx.invoked_subcommand is None:
        print('Welcome to pyeth-api-server!')
        slogging.configure(':DEBUG')
        blockchain_proxy = ctx.invoke(app, **kwargs)

        if pyeth_api == None:
            pyeth_api = _get_pyeth_api(kwargs['inst'],blockchain_proxy)

        domain_list = ['*']
        if kwargs['rpccorsdomain']:
            if ',' in kwargs['rpccorsdomain']:
                for domain in kwargs['rpccorsdomain'].split(','):
                    domain_list.append(str(domain))
            else:
                domain_list.append(str(kwargs['rpccorsdomain']))
        if ctx.params['rpc']:
            rest_api = RestAPI(pyeth_api)
            api_server = APIServer(
                rest_api,
                cors_domain_list=domain_list,
            )
            (api_host, api_port) = split_endpoint(kwargs['rpcaddress'])
            server1 = Greenlet.spawn(
                api_server.run,
                api_port,
                debug=False,
                use_evalex=False
            )

            print(
                'The pyeth API RPC server is now running at http://{}:{}/.\n\n'.format(
                    api_host,
                    api_port,
                )
            )

        admin_account = str(kwargs['admin'])
        """======创建链代理，并部署相关合约============"""
        proxy1 = pyeth_api.new_blockchain_proxy("ethereum","kovan",os.getcwd()+'/'+sys.argv[0]+'/keystore',admin_account)
        proxy2 = pyeth_api.new_blockchain_proxy("atmchain","118.31.71.12:21024",os.getcwd()+'/'+sys.argv[0]+'/keystore',admin_account)
        
        admin_password = str(kwargs['password'])
        if admin_password ==None:
            admin_password = click.prompt('Enter the password to unlock admin account %s' % admin_account, default='', hide_input=True,
                                confirmation_prompt=False, show_default=False)

        account_atmchain = pyeth_api.get_admin_account('atmchain')
        admin_password_atmchain =admin_password
        pyeth_api.set_admin_password('atmchain',admin_password_atmchain)

        account_ethereum = pyeth_api.get_admin_account('ethereum')
        admin_password_ethereum = admin_password
        pyeth_api.set_admin_password('ethereum',admin_password_ethereum)

        ContractAddress = custom_contract_events.__contractInfo__['ContractAddress']['address']

        if ContractAddress == "":
            ContractAddress_proxy = proxy2.deploy_contract( 
                account_atmchain,
                custom_contract_events.__contractInfo__['ContractAddress']['file'], 'ContractAddress',
                password=admin_password_atmchain,
            )
        else:
            ContractAddress_proxy = proxy2.attach_contract(
                'ContractAddress',
                contract_file = custom_contract_events.__contractInfo__['ContractAddress']['file'],
                contract_address = unhexlify(ContractAddress), #ContractAddress.address, 
                attacher = account_atmchain,
                password=admin_password_atmchain,
            )
        
        if custom_contract_events.__contractInfo__['ForeignBridge']['address'] == "":
            foreignbridge_proxy = proxy2.deploy_contract( 
                account_atmchain,
                custom_contract_events.__contractInfo__['ForeignBridge']['file'], 'ForeignBridge',
                (1,[account_atmchain]),
                password=admin_password_atmchain
                )
            txhash = ContractAddress_proxy.set_foreigin_bridge('0x'+hexlify(foreignbridge_proxy.address))
            result, txhash = proxy2.poll_contarct_transaction_result(txhash) 
            if result == "transaction execute failed":
                raise RuntimeError("transaction execute failed. txhash:{}".format(txhash))
        elif ContractAddress_proxy.foreigin_bridge() != custom_contract_events.__contractInfo__['ForeignBridge']['address']:
            print('[**WARNING**]foreigin_bridge is already deployed:{}. while configed:{}'.format(ContractAddress_proxy.foreigin_bridge(),custom_contract_events.__contractInfo__['ForeignBridge']['address']))
        
        if custom_contract_events.__contractInfo__['ATMToken']['address'] == "":
            ATMToken_proxy = proxy1.deploy_contract( 
                account_ethereum,
                custom_contract_events.__contractInfo__['ATMToken']['file'], 'ATMToken',
                password=admin_password_ethereum
                )
            txhash = ContractAddress_proxy.set_atm_token('0x'+hexlify(ATMToken_proxy.address))
            result, txhash = proxy1.poll_contarct_transaction_result(txhash) 
            if result == "transaction execute failed":
                raise RuntimeError("transaction execute failed. txhash:{}".format(txhash))
        elif ContractAddress_proxy.atm_token() != custom_contract_events.__contractInfo__['ATMToken']['address']:
            print('[**WARNING**]atm_token is already deployed:{}. while configed:{}'.format(ContractAddress_proxy.atm_token(),custom_contract_events.__contractInfo__['ATMToken']['address']))
        
        if custom_contract_events.__contractInfo__['HomeBridge']['address'] == "":
            ATMToken_proxy = proxy1.deploy_contract( 
                account_ethereum,
                custom_contract_events.__contractInfo__['HomeBridge']['file'], 'HomeBridge',
                (1,[account_ethereum]),
                password=admin_password_ethereum
                )
            txhash = ContractAddress_proxy.set_home_bridge('0x'+hexlify(ATMToken_proxy.address))
            result, txhash = proxy1.poll_contarct_transaction_result(txhash) 
            if result == "transaction execute failed":
                raise RuntimeError("transaction execute failed. txhash:{}".format(txhash))
        elif ContractAddress_proxy.home_bridge() != custom_contract_events.__contractInfo__['HomeBridge']['address']:
            print('[**WARNING**]HomeBridge is already deployed:{}. while configed:{}'.format(ContractAddress_proxy.home_bridge(),custom_contract_events.__contractInfo__['HomeBridge']['address']))
        
        """=======end============="""

        if ctx.params['console']:
            console = Console(pyeth_api)
            console.start()
            server2 = Greenlet.spawn(
                console.run
            )
        # wait for interrupt
        event = gevent.event.Event()
        gevent.signal(signal.SIGQUIT, event.set)
        gevent.signal(signal.SIGTERM, event.set)
        gevent.signal(signal.SIGINT, event.set)

        gevent.signal(signal.SIGUSR1, toogle_cpu_profiler)
        gevent.signal(signal.SIGUSR2, toggle_trace_profiler)

        event.wait()
        pyeth_api.listen_contract_events.stop()
        pyeth_api.atm_deposit_worker.stop()
        if server1 != None:
            server1.kill(block=True, timeout=10)
        if server2 != None:
            server2.kill(block=True, timeout=10)
    else:
        # Pass parsed args on to subcommands.
        ctx.obj = kwargs