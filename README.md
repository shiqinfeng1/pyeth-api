# pyeth-api
A set of easy-to-use APIs for access to Ethereum written in python, very friendly and accessible to Ethereum Dapp developers. 
It supports JSONRPC or import directly in the application.

pyeth-api runs on Python 2.7, for Pyethapp is only support for Python 2.7.

## pre-prepare
1. recommended install pyenv tools to manage virtualenv
1. install solc

## fetures
1. auto smart contract deploy
1. cross-chain ethereum token transfer
1. support api: json-rpc, console, direct-call


## functions
1. accounts manage
1. contract deploy
1. contract operation proxy
1. blockchain info

## usage
1. drop your contract to smart_contracts folder
1. in the custom/custom_contract_events.py, add your contract event filter condition which needs to be listened 
1. to be continue...

  start command:
  ```
  python  pyethapi --console
  ```
  command args:
  ```
  --rpc / --no-rpc      Start with or without the RPC server.  [default: True]
  --console             Start the interactive console
  --rpccorsdomain TEXT  Comma separated list of domains to accept cross origin
                        requests.  [default: http://localhost:*/*]
  --rpcaddress TEXT     "host:port" for the service to listen on.  [default:
                        0.0.0.0:40001]
  --gas-price INTEGER   Set the Ethereum transaction's gas price  [default:
                        20000000000]
  --keystore-path PATH  If you have a non-standard path for the ethereum
                        keystore directory provide it using this argument.
  --help                Show this message and exit.
  ```

## thanks
thanks for projects of Raiden Networks 
