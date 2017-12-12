import click
import gevent
import gevent.monkey
import signal
from pyethapi.service import constant 
from raipyethapi.service.utils import (
    split_endpoint
)

def toogle_cpu_profiler(raiden):
    try:
        from raiden.utils.profiling.cpu import CpuProfiler
    except ImportError:
        slogging.get_logger(__name__).exception('cannot start cpu profiler')
        return

    if hasattr(raiden, 'profiler') and isinstance(raiden.profiler, CpuProfiler):
        raiden.profiler.stop()
        raiden.profiler = None

    elif not hasattr(raiden, 'profiler') and raiden.config['database_path'] != ':memory:':
        raiden.profiler = CpuProfiler(raiden.config['database_path'])
        raiden.profiler.start()


def toggle_trace_profiler(raiden):
    try:
        from raiden.utils.profiling.trace import TraceProfiler
    except ImportError:
        slogging.get_logger(__name__).exception('cannot start tracer profiler')
        return

    if hasattr(raiden, 'profiler') and isinstance(raiden.profiler, TraceProfiler):
        raiden.profiler.stop()
        raiden.profiler = None

    elif not hasattr(raiden, 'profiler') and raiden.config['database_path'] != ':memory:':
        raiden.profiler = TraceProfiler(raiden.config['database_path'])
        raiden.profiler.start()

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

OPTIONS = [
    click.option(
        '--keystore-path',
        help=('If you have a non-standard path for the ethereum keystore directory'
              ' provide it using this argument.'),
        default=None,
        type=click.Path(exists=True),
        show_default=True,
    ),
    click.option(
        '--gas-price',
        help="Set the Ethereum transaction's gas price",
        default=constant.GAS_PRICE,
        type=int,
        show_default=True,
    ),
    click.option(
        '--eth-rpc-endpoint',
        help='"host:port" address of ethereum JSON-RPC server.\n'
        'Also accepts a protocol prefix (http:// or https://) with optional port',
        default='127.0.0.1:8545',  # geth default jsonrpc port
        type=str,
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
        '--rpc/--no-rpc',
        help=(
            'Start with or without the RPC server.'
        ),
        default=True,
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
def app(address,
        keystore_path,
        gas_price,
        eth_rpc_endpoint,
        rpccorsdomain,
        rpc_address,
        rpc,
        console):

    # pylint: disable=too-many-locals,too-many-branches,too-many-statements,unused-argument

    from pyethapi.service.blockchain import BlockChainService

    (api_host, api_port) = split_endpoint(rpc_address)


    endpoint = eth_rpc_endpoint
    eth_rpc_host = 8545
    if ':' not in endpoint:  # no port was given in url
        eth_rpc_host = endpoint
    else:
        eth_rpc_host, eth_rpc_port = split_endpoint(endpoint)

    rpcclient = BlockChainService(
        'BCS-'+eth_rpc_host+eth_rpc_host, eth_rpc_host,eth_rpc_port,os.getcwd()+'/keystore')

    # this assumes the eth node is already online
    if not check_json_rpc(rpcclient.jsonrpc_client):
        sys.exit(1)


@click.group(invoke_without_command=True)
@options
@click.pass_context
def run(ctx, **kwargs):
    if ctx.invoked_subcommand is None:
        print('Welcome to pyeth-api-server!')
        slogging.configure(':DEBUG')

        app_ = ctx.invoke(app, **kwargs)
        domain_list = []
        if kwargs['rpccorsdomain']:
            if ',' in kwargs['rpccorsdomain']:
                for domain in kwargs['rpccorsdomain'].split(','):
                    domain_list.append(str(domain))
            else:
                domain_list.append(str(kwargs['rpccorsdomain']))
        if ctx.params['rpc']:
            raiden_api = RaidenAPI(app_.raiden)
            rest_api = RestAPI(raiden_api)
            api_server = APIServer(
                rest_api,
                cors_domain_list=domain_list,
                eth_rpc_endpoint=ctx.params['eth_rpc_endpoint'],
            )
            (api_host, api_port) = split_endpoint(kwargs['rpcaddress'])
            api_server.start(api_host, api_port)

            print(
                'The pyeth API RPC server is now running at http://{}:{}/.\n\n'.format(
                    api_host,
                    api_port,
                )
            )

        if ctx.params['console']:
            console = Console(app_)
            console.start()

        # wait for interrupt
        event = gevent.event.Event()
        gevent.signal(signal.SIGQUIT, event.set)
        gevent.signal(signal.SIGTERM, event.set)
        gevent.signal(signal.SIGINT, event.set)

        gevent.signal(signal.SIGUSR1, toogle_cpu_profiler)
        gevent.signal(signal.SIGUSR2, toggle_trace_profiler)

        event.wait()

        try:
            api_server.stop()
        except NameError:
            pass

        app_.stop()
    else:
        # Pass parsed args on to subcommands.
        ctx.obj = kwargs