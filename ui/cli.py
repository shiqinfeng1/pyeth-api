import click
import os
import gevent
import gevent.monkey
import signal
from gevent import Greenlet
from service import constant 
from service.utils import (
    split_endpoint
)
from api.rest import APIServer, RestAPI
from ethereum import slogging
from api.python import PYETHAPI
from applications.twitter_rewards_plan.twitter_rewards_plan import PYETHAPI_ATMCHAIN_REWARDS_PLAN
from api.python import PYETHAPI_ATMCHAIN
from ui.console import Console

pyethapi = dict()
pyethapi['default'] = PYETHAPI
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
        default='atmchain_rewards_plan',
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
        inst):

    # pylint: disable=too-many-locals,too-many-branches,too-many-statements,unused-argument

    from service.blockchain import BlockChainService

    blockchain_service = BlockChainService()

    return blockchain_service

def  _get_pyeth_api(inst,blockchain_proxy):
    if inst in pyethapi.keys():
        pyeth_api = pyethapi[inst](blockchain_proxy)
    else:
        pyeth_api = pyethapi['default'](blockchain_proxy)
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
        domain_list = ['*']
        if kwargs['rpccorsdomain']:
            if ',' in kwargs['rpccorsdomain']:
                for domain in kwargs['rpccorsdomain'].split(','):
                    domain_list.append(str(domain))
            else:
                domain_list.append(str(kwargs['rpccorsdomain']))
        if ctx.params['rpc']:
            if pyeth_api == None:
                pyeth_api = _get_pyeth_api(kwargs['inst'],blockchain_proxy)
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

        if ctx.params['console']:
            if pyeth_api == None:
                pyeth_api = _get_pyeth_api(kwargs['inst'],blockchain_proxy)

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
        if server1 != None:
            server1.kill(block=True, timeout=10)
        if server2 != None:
            server2.kill(block=True, timeout=10)
    else:
        # Pass parsed args on to subcommands.
        ctx.obj = kwargs