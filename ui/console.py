# -*- coding: utf-8 -*-
from __future__ import print_function

import cStringIO
import json
import sys
import time
from logging import StreamHandler, Formatter

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
from service.utils import  get_contract_path, safe_address_decode

# ipython needs to accept "--gui gevent" option
IPython.core.shellapp.InteractiveShellApp.gui.values += ('gevent',)
inputhook_manager.register('gevent')(GeventInputHook)


def print_usage():
    print("\t{}use `{}account{}` to interact with the account manager.".format(
        bc.OKBLUE, bc.HEADER, bc.OKBLUE))
    print("\tuse `{}chain{}` to interact with the blockchain.".format(bc.HEADER, bc.OKBLUE))
    print("\tuse `{}help(<topic>){}` for help on a specific topic.".format(bc.HEADER, bc.OKBLUE))
    print("\ttype `{}usage(){}` to see this help again.".format(bc.HEADER, bc.OKBLUE))
    print("\n" + bc.ENDC)


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

        self.console_locals = dict(
            chain=ChainTools(
                self.pyeth_api
            ),
            usage=print_usage,
        )

    def run(self):
        self.interrupt.wait()
        print('\n' * 2)
        print("Entering Console" + bc.OKGREEN)
        print("Tip:" + bc.OKBLUE)
        print_usage()

        # Remove handlers that log to stderr
        root = getLogger()
        for handler in root.handlers[:]:
            if isinstance(handler, StreamHandler) and handler.stream == sys.stderr:
                root.removeHandler(handler)

        stream = cStringIO.StringIO()
        handler = StreamHandler(stream=stream)
        handler.formatter = Formatter("%(levelname)s:%(name)s %(message)s")
        root.addHandler(handler)

        def lastlog(n=10, prefix=None, level=None):
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


class ChainTools(object):
    def __init__(self, pyeth_api):
        self.pyeth_api = pyeth_api
        self.blockchain_service = pyeth_api.blockchain_service

    def new_blockchain_proxy(self, chain_name,host,port):
        if self.blockchain_service.blockchain_proxy[chain_name] == None:
            ethereum_proxy = self.blockchain_service.new_blockchain_proxy(
                chain_name, host, port, os.getcwd()+'/keystore')
        return True

    def blockchain_proxy_list(self, host, port):
        proxy_list = list(self.blockchain_service.blockchain_proxy.keys())
        print proxy_list

