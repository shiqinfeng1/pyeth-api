# pyeth-api
A set of easy-to-use APIs for interactive with Ethereum smart contract written in python, very friendly and accessible to Ethereum Dapp developers. 
It supports JSONRPC or import directly in the application.

pyeth-api runs on Python 2.7, for Pyethapp is only support for Python 2.7.

## 1 环境和安装
1. recommended install “pyenv” tools to manage virtualenv
1. install solc
```
    pip install py-solc
    python -m solc.install v0.4.15
    //检查是否安装成功. 注意将路径修改为实际安装用户的路径
    ls /users/shiqinfeng/.py-solc/solc-v0.4.15/bin
    //注意写入的配置文件，各个系统可能有所不同
    echo "export SOLC_BINARY=/users/shiqinfeng/.py-solc/solc-v0.4.15/bin/solc" >> ~/.bash_profile
    source ~/.bash_profile
    echo $SOLC_BINARY
```

安装依赖：
```
    cd pyethapi/
    pip install -r requirements.txt
```
## 2 启动命令
```
//在pyethapi的上一级目录执行启动命令
cd /Users/shiqinfeng/Documents/workspace/workspace_python/
python pyethapi --console

python pyethapi --admin "0x5252781539b365e08015fa7ed77af5a36097f39d" --password "123456" --console
```
## 3 启动参数说明
```
--rpc / --no-rpc      是否开启RPC服务.[默认:开启].
--console             启动交互控制台.[默认:关闭].
--rpccorsdomain TEXT  跨域配置 [默认: http://localhost:*/*].
--rpcaddress TEXT     rpc服务的监听地址 "host:port" [默认: 0.0.0.0:40001].
--gas-price INTEGER   以太坊交易默认gas价格 [默认: 20000000000].
--inst                指定默认启动的实例名字.[默认是atmchain_bridge]
--help                显示本帮助.
```

## 4 控制台操作命令
操作命令支持tab自动补全。操作命令包括一个基础的chain管理工具， 以及各个在上面开发的app工具。
## 4.1 Usage()
显示当前可用的命令。
## 4.2 chain：链管理
## 4.2.1 连接到一个以太坊节点：

    >chain.new_blockchain_proxy('eth1','192.168.15.12:8545')
    输出：
    =======================================
    chain_name          : eth1
    host                : 192.168.15.12
    port                : 8545
    keystore_path       : /Users/shiqinfeng/Documents/workspace/workspace_python/pyethapi/keystore
    default accounts    : ['e17a73ecb575bb13cc735b88f818b5cec2a42b13', '5252781539b365e08015fa7ed77af5a36097f39d', '63f1de588c7ce855b66cf24b595a8991f921130d', 'a1629411f4e8608a7bb88e8a7700f11c59175e72', '4fa07e11d6170b56afecb85f20028ea6687ddd62', 'b16bccd8a93aabea218a25736b573d8f76479144', '8398895dc442c0d2ba5d42707133582babfc1b0b']

其中默认账户数据路径是：

    /Users/shiqinfeng/Documents/workspace/workspace_python/pyethapi/keystore

也可以在命令参数中指定：

    chain.new_blockchain_proxy('eth1','192.168.15.12:8545',keystore_path='./keysotre')

除了直接指定节点地址外， 还支持公链和测试链的别名连接,支持'mainnet', 'ropsten', 'kovan', 'rinkeby'链：

    chain.new_blockchain_proxy('eth2','mainnet')
    chain.new_blockchain_proxy('eth3','ropsten')
    chain.new_blockchain_proxy('eth4','kovan')
    chain.new_blockchain_proxy('eth5','rinkeby')

## 4.2.2 查询当前所有链代理：

    chain.blockchain_proxy_list()

## 4.2.3 设置调试打印等级：

    chain.set_log_level('debug')
    //等级如下
    'critical','error','warn','warning','info','debug','notest'

## 4.2.4 导入账户：

    chain.new_account('eth1',key='...')  //key是私钥

## 4.2.5 查询链上原生币的余额：

    chain.query_currency_balance(chain_name,account)

## 4.2.6 查询链上代币的余额：

    chain.query_token_balance(chain_name,account)

## 4.2.2 查看当前连接的节点上所有账户

    chain.eth_accounts_list('eth1')
    //输出
    ------------------------------------
    [ethereum user accounts]:
    0: 0xe17a73ecb575bb13cc735b88f818b5cec2a42b13
    1: 0x5252781539b365e08015fa7ed77af5a36097f39d
    2: 0x63f1de588c7ce855b66cf24b595a8991f921130d
    3: 0xa1629411f4e8608a7bb88e8a7700f11c59175e72
    4: 0x4fa07e11d6170b56afecb85f20028ea6687ddd62
    5: 0xb16bccd8a93aabea218a25736b573d8f76479144
    6: 0x8398895dc442c0d2ba5d42707133582babfc1b0b
    ------------------------------------

查看ATM账户：chain.ATM_accounts_list()

## 4.2.3 查看私钥对应的公钥

    chain.check_account(privkey='...')

## 4.2.4 查看当前所有连接的节点的信息

    chain.blockchain_proxy_list()
    =======================================
    chain_name          : eth
    endpoint            : https://kovan.infura.io/SaTkK9e9TKrRuhHg
    keystore_path       : /Users/shiqinfeng/Documents/workspace/workspace_python/pyethapi/keystore
    default accounts    : ['e17a73ecb575bb13cc735b88f818b5cec2a42b13', '5252781539b365e08015fa7ed77af5a36097f39d', '63f1de588c7ce855b66cf24b595a8991f921130d', 'a1629411f4e8608a7bb88e8a7700f11c59175e72', '4fa07e11d6170b56afecb85f20028ea6687ddd62', 'b16bccd8a93aabea218a25736b573d8f76479144', '8398895dc442c0d2ba5d42707133582babfc1b0b']
    =======================================
    chain_name          : eth2
    endpoint            : https://mainnet.infura.io/SaTkK9e9TKrRuhHg
    keystore_path       : /Users/shiqinfeng/Documents/workspace/workspace_python/pyethapi/keystore
    default accounts    : ['e17a73ecb575bb13cc735b88f818b5cec2a42b13', '5252781539b365e08015fa7ed77af5a36097f39d', '63f1de588c7ce855b66cf24b595a8991f921130d', 'a1629411f4e8608a7bb88e8a7700f11c59175e72', '4fa07e11d6170b56afecb85f20028ea6687ddd62', 'b16bccd8a93aabea218a25736b573d8f76479144', '8398895dc442c0d2ba5d42707133582babfc1b0b']
    =======================================
    chain_name          : eth1
    host                : 192.168.15.12
    port                : 8545
    keystore_path       : /Users/shiqinfeng/Documents/workspace/workspace_python/pyethapi/keystore
    default accounts    : ['e17a73ecb575bb13cc735b88f818b5cec2a42b13', '5252781539b365e08015fa7ed77af5a36097f39d', '63f1de588c7ce855b66cf24b595a8991f921130d', 'a1629411f4e8608a7bb88e8a7700f11c59175e72', '4fa07e11d6170b56afecb85f20028ea6687ddd62', 'b16bccd8a93aabea218a25736b573d8f76479144', '8398895dc442c0d2ba5d42707133582babfc1b0b']

## 4.2.5 查询账户余额

    chain.query_eth_balance('eth1','5252781539b365e08015fa7ed77af5a36097f39d')
    ------------------------------------
    5252781539b365e08015fa7ed77af5a36097f39d: 9.04619364786e+56

查看账户atm余额：chain.query_atmchain_balance()


# 4.3 JSON-RPC服务

服务地址： [http://](http://192.168.15.12:40001/api/v1/)[<IP>[:40001/api/v1/](http://192.168.15.12:40001/api/v1/)xxx

http请求举例：

    curl http://192.168.15.12:40001/api/v1/asset -X POST -d '{"chain_name":"poa","user_address":"0x5252781539B365E08015fA7ED77af5a36097f39d","name":"a","symbol":"22","decimals":2,"total_suply":11111}' -H "Content-Type: application/json"
    返回结果：
    {
        "id": "1",
        "result": {
            "contract_address": "113d12442d889fbf3ed868c2a717f1654257a229"
        }
    }
    
    #curl http://localhost:21024 -X POST -H "Content-Type: application/json" -d '{"params": ["0x3ebd235d29214700c5fd048a0330bc8a6ccd236d", "latest"], "jsonrpc": "2.0", "method": "eth_getCode", "id": 23}'

## 4.3.x 查询指定账户的nonce

    curl http://localhost:40001/api/v1/QueryNonce -X POST -d '{"user":"0x5252781539B365E08015fA7ED77af5a36097f39d"}' -H "Content-Type: application/json"
    {"nonoce": 2}
    
    curl http://localhost:40001/api/v1/QueryNonce -X POST -d '{"chain_name":"atmchain","user":"0x5252781539B365E08015fA7ED77af5a36097f39d"}' -H "Content-Type: application/json"
    {"nonoce": 143}

## 4.3.x 查询单次跨链转移ATM的上限金额

    curl http://localhost:40001/api/v1/QueryDepositLimit -X POST -d '{}' -H "Content-Type: application/json"

返回结果

    {"deposit_limit": 1000000000000}

## 4.3.x 发送离线能交易

    curl http://47.96.152.78:40001/api/v1/SendRawTransaction -X POST -d '{"chain_name":"ethereum","signed_data":"0xf8ab81828502540be400830186a0941343f98dcb7c867d553696d506cc87da995b75d280b844a9059cbb00000000000000000000000069eb6e2b2dc66268482467b9b35369dc5c656cf000000000000000000000000000000000000000000000000000000000069f40601ca08428163aa611fa0aaba51bc502dc6eb9826513738f0558d559e48199957f2bffa07d5e1c5a78fd9221fd9d6c7c6081a541966517cb2a9a42e0013d92afa9d2b311"}' -H "Content-Type: application/json"

返回结果

    {"transaction_hash": "0xc7a542f41ba6f7806ede3656d2827bdd5c881c69b467aef5ff3fccf570c77cd0"}

## 4.3.x 查询账户余额

Pre-require：已连接到链节点

Request method：/api/v1/QueryBalance

Request Data: 

    curl http://localhost:40001/api/v1/QueryBalance -X POST -d '{"user":"0x5252781539B365E08015fA7ED77af5a36097f39d"}' -H "Content-Type: application/json"
    

Request Arguments：

    "user":用户地址

Request Result:

    {"balance": {"ATM_balance_ethereum": 10000000000000000, "ETH_balance": 798874094000000000, "ATM_balance_atmchain": 904625697166532776746648320380374180102671755189916883885663508199821325312}}

## 4.3.x 发布ERC20 资产

Pre-require：已连接到链节点

Request method：/api/v1/asset 

Request Data: 

    {
    		"chain_name":"poa",
    		"user_address":"0x5252781539B365E08015fA7ED77af5a36097f39d",
    		"name":"custom token",
    		"symbol":"CT",
    		"decimals":10,
    		"total_suply":10000000000
    }

Request Arguments：

    "chain_name":发布资产的链名字
    "user_address":发布资产的用户地址
    "name":资产名字
    "symbol":资产符号
    "decimals":资产精度
    "total_suply":发行总量

Request Result:

    {
        
        "contract_address": "0x113d12442d889fbf3ed868c2a717f1654257a229"
        
    }

## 4.3.x 查询指定账户ATM跨链锁定/解锁记录

Pre-require：通过ATMchain页面发送锁定请求

Request method：/api/v1/QueryBridgeStatus

Request Data: 

    {
    			"bridge_type":"deposit/withdraw",
    			"transaction_hash":"0x......",
    			"user_address":"0x5252781539B365E08015fA7ED77af5a36097f39d",
    }

Request Arguments：

    "bridge_type":"ethereum/atmchain",
    "transaction_hash": 用户向homebridge合约转账ATM的交易hash
    "user_address":查询账户地址

Request Result:

    {
    	'ID':1,
    	'USER_ADDRESS':"...",
    	'AMOUNT':"...",
    	'STAGE':"...",
    	'CHAIN_NAME_SRC':"...",
    	'TRANSACTION_HASH_SRC':"...",
    	'BLOCK_NUMBER_SRC':"...",
    	'CHAIN_NAME_DEST':"...",
    	'TRANSACTION_HASH_DEST':"...",
    	'BLOCK_NUMBER_DEST':"...",
    	'TIME_STAMP':"...",]}
        
# 6 开发一个新的应用

第一步。在applications下新建app的目录，并新建相应的py文件。

例如：新建文件夹twitter_rewards_plan，文件twitter_rewards_plan.py

第二步。实现功能。

第三步。在cli.py中，引入新加的模块，例如PYETHAPI_ATMCHAIN_REWARDS_PLAN，并配置全局变量pyethapi，key为app的名字：

    from applications.twitter_rewards_plan.twitter_rewards_plan import PYETHAPI_ATMCHAIN_REWARDS_PLAN
    pyethapi['atmchain_rewards_plan'] = PYETHAPI_ATMCHAIN_REWARDS_PLAN

在启动pyethapi时， `--inst`参数可以指定该app的名字，启动后可以在**控制台和rest接口**中使用该app的操作接口。

第四步。在console.py中，实现该应用的控制台接口，例如AppTwitterTools。该接口继承自ATMChainTools，因此，可以使用ATMChainTools中的所有已经实现的公共的接口。并在console_locals中增加对新的app接口的支持，如下：

    App_twitter_tools=AppTwitterTools(ATMChain_tools)
    self.console_locals  = dict(
        chain=ATMChain_tools,
        app_twitter=App_twitter_tools,
        usage=ATMChain_print_usage,
    )

其中key：`app_twitter`在pyethapi启动后可以直接用来调用接口函数了。

# 7 部署一个新合约

- 编写新合约，放在smart_contarcts目录下
- 合约调用方式举例：

      ethereum_proxy = self.pyeth_api._get_chain_proxy('poa')
      sender = ethereum_proxy.account_manager.admin_account
      
      userToken = self.pyeth_api._deploy_contract( 
           sender,  //发布合约的账户
           'poa',   //链名字
           'userToken.sol', 'userToken',  //合约文件和名字
           (hexlify(user_address),100000,'REX',8,'REX Token'), //合约参数
           password = '123456',  //可以指定发布者账户的密码，如不指定，可以在命令行输入
      )
      address = userToken.address  //返回的合约地址

- 在 custom/custom_contract_events.py中定义事件监听过滤器,例如定义一个Minted事件：

      def ERC223Token_Minted_filter_condition(_to):
          
          def filter(event):
              if event['_event_type'] != 'Minted':
                  return False
              if normalize_address(event['_to']) ==  normalize_address(_to):
                  return True
              return False
      
          return filter

  名字格式定义：<合约名字>_<事件名字>_filter_condition(过滤参数)，

  返回true：表示匹配到事件；返回false：表示没有匹配到事件；

  在全局变量__**conditionSet__**中，注册该过滤器,key是<合约名字>_<事件名字>：

      'ERC223Token_Minted': ERC223Token_Minted_filter_condition,
