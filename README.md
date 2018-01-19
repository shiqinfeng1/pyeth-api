# pyeth-api
A set of easy-to-use APIs for access to Ethereum written in python, very friendly and accessible to Ethereum Dapp developers. 
It supports JSONRPC or import directly in the application.

pyeth-api runs on Python 2.7, for Pyethapp is only support for Python 2.7.

## pre-prepare
1. recommended install pyenv tools to manage virtualenv
1. install solc
```
    pip install py-solc
    python -m solc.install v0.4.15
    echo "export SOLC_BINARY=/root/.py-solc/solc-v0.4.15/bin/solc" >> ~/.bash_profile  // /etc/bash.bashrc
    echo $SOLC_BINARY
```
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
1. in the custom/custom_contract_events.py,register your filter function to `__conditionSet__`
1. write operate api. 
 example:
 ```
 class PYETHAPI_ATMCHAIN_REWARDS_PLAN(PYETHAPI_ATMCHAIN):
    def __init__(self,blockchain_service):
        print('init PYETHAPI_ATMCHAIN_REWARDS_PLAN ...')
        super(PYETHAPI_ATMCHAIN_REWARDS_PLAN, self).__init__(blockchain_service)

    def deploy_twitter_rewards_contract(self,deployer=None): 
        ethereum_proxy = self._get_chain_proxy('ethereum')
        if deployer == None:
            ethereum_sender = ethereum_proxy.account_manager.admin_account
        else:
            ethereum_sender = deployer

        self._deploy_contract( 
            ethereum_sender, 
            'ethereum',
            'twitter.sol', 'TwitterAccount',
            )
 ```

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
                        20,000,000,000]
  --inst                to start with an app inst. one of [default, atmchain, atmchain_rewards_plan]
  --help                Show this message and exit.
 
  ```

## thanks
thanks for projects of Raiden Networks 
