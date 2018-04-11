# -*- coding: utf-8 -*-
import os
import pymysql
from ethereum.utils import normalize_address
from binascii import hexlify, unhexlify
from service.utils import (
    address_encoder,
    address_decoder,
)
import time
import gevent
from gevent import Greenlet
from uuid import uuid4
from service import constant,accounts_manager
from service.accounts_manager import Account,find_keystoredir
from ethereum.utils import encode_hex
import custom.custom_contract_events as custom_contract_events

class PYETHAPI(object):
    """ CLI interface. """

    def __init__(self,blockchain_service):
        print('init pyeth-api ...')
        self.blockchain_service = blockchain_service

    @property
    def adminAddress(self):
        return self.blockchain_service.adminAddress
    #raise NotImplementedError()

    def _get_chain_proxy(self,chain_name):
        assert chain_name in self.blockchain_service.blockchain_proxy.keys()
        _proxy = self.blockchain_service.blockchain_proxy[chain_name]
        return _proxy

    def _get_contract_address(self,chain_name,contract_name): 
        _proxy = self._get_chain_proxy(chain_name)
        _contract_proxy = _proxy.attach_contract(contract_name)
        return _contract_proxy.address if _contract_proxy != None else None


    """新建区块链代理"""
    def new_blockchain_proxy(self, chain_name,endpoint,keystore_path):
        assert keystore_path != None
        if chain_name not in self.blockchain_service.blockchain_proxy.keys():
            _proxy = self.blockchain_service.new_blockchain_proxy(
                chain_name, endpoint, keystore_path)
        return _proxy

    """查询当前区块链所有代理"""
    def blockchain_proxy_list(self):
        proxy_list = list(self.blockchain_service.blockchain_proxy.keys())
        return proxy_list
        
    """设置管理员账户"""
    def set_admin_account(self,chain_name,old_address,admin_address):
        _proxy = self._get_chain_proxy(chain_name)
        _proxy.account_manager.set_admin_account(old_address,admin_addess)

    """创建新账户"""
    def new_account(self, chain_name, password=None, key=None):
        assert isinstance(key,str) and len(key)==64
        id_ = uuid4()
        _proxy = self._get_chain_proxy(chain_name)

        if password is None:
            password = ''
        account = Account.new(password, key=key, uuid=id_)
        account.path = os.path.join(_proxy.account_manager.keystore_path, '0x'+encode_hex(account.address))
        try:
            _proxy.account_manager.add_account(account) 
        except IOError:
            print('Could not write keystore file. Make sure you have write permission in the '
                    'configured directory and check the log for further information.')
            sys.exit(1)
        else:
            print('Account creation successful')
            print('  Address: {}'.format(encode_hex(account.address)))
            print('       Id: {}'.format(account.uuid))

    """查询当前keystore下所有账户"""
    def eth_accounts_list(self,chain_name): 
        _proxy = self._get_chain_proxy(chain_name)
        return list(_proxy.account_manager.accounts.keys())

    """原生币转账"""
    def transfer_currency(self,chain_name,sender,to,amount):
        _proxy = self._get_chain_proxy(chain_name)
        amount = amount * constant.WEI_TO_ETH
        _proxy.transfer_currency(sender,to,amount)
    
    """token转账"""
    def transfer_token(self,chain_name,contract_address,sender,to,amount,is_erc223=False):
        _proxy = self._get_chain_proxy(chain_name)
        contract_proxy = _proxy.attach_contract(
            'Token',
            contract_file='Token.sol',
            contract_address=contract_address,
            attacher=sender,
        )
        block_number = _proxy.block_number()
        #由于pythpn版本以太坊暂时无法处理同名函数, 暂时通过flag来区分
        if is_erc223 == True:
            txhash = contract_proxy.transfer(to,amount*constant.ATM_DECIMALS,'')
        else:
            txhash = contract_proxy.transfer(to,amount*constant.ATM_DECIMALS)

        _proxy.poll_contarct_transaction_result(txhash,block_number,contract_proxy,'Transfer',to)

class DBService(object):

    def __init__(self):
        self.db = None
        self.polling_events_callback = dict()
        self.polling_events_callback['ethereum_ATMToken_Transfer_offline'] = self.ethereum_ATMToken_Transfer_offline_to_DB
        self.polling_events_callback['ethereum_ATMToken_Transfer'] = self.ethereum_ATMToken_Transfer_to_DB
        self.polling_events_callback['atmchain_ForeignBridge_Deposit'] = self.atmchain_ForeignBridge_Deposit_to_DB

    def ethereum_ATMToken_Transfer_offline_to_DB(self, sql_sets, tx_hash, *args):
        
        """检查数据库bridge中是否存在DEPOSIT表， 如果不存在，新建该表"""
        if db.is_table_exist('DEPOSIT', 'bridge') != None:
            self.create_table('DEPOSIT', '...')

        sql = sql_sets[0](*args)
        self.insert_into_sql([sql])
  
    def ethereum_ATMToken_Transfer_to_DB(self, sql_sets, tx_hash, *args):
        
        """检查数据库bridge中是否存在DEPOSIT表， 如果不存在，新建该表"""
        if db.is_table_exist('DEPOSIT', 'bridge') != None:
            self.create_table('DEPOSIT', '...')

        """检查tx_hash对应记录数据是否存在"""
        result = self.find_rows('DEPOSIT',"transaction_hash = {}".format(tx_hash))
        if result != None:
            sql = sql_sets[1](*args)
        else:
            sql = sql_sets[0](*args)
  
        self.insert_into_sql([sql])

    def atmchain_ForeignBridge_Deposit_to_DB(self, sql_sets, tx_hash, *args):
        
        """检查数据库bridge中是否存在DEPOSIT表， 如果不存在，新建该表"""
        if db.is_table_exist('DEPOSIT', 'bridge') != None:
            return

        sql = sql_sets[0](*args)

        self.insert_into_sql([sql])

    def connect(self):
        self.db = pymysql.connect(
            host=ip, 
            port=port, 
            user=mysql_user, 
            passwd=mysql_passwd, 
            db=database, 
            )

    def disconnect(self):
        self.db.close()

    def create_table(self, tablename, columns):
        type_data = ['int', 'double(10,3)']
        cursor = self.db.cursor()
        sql="create table %s("%(tablename,)
        sql+=columns+')'
        try:
            cursor.execute(sql)
            print("Table %s is created"%tablename)
        except:
            self.db.rollback()

    def is_table_exist(self, tablename,dbname):
        cursor=self.db.cursor()
        sql="select table_name from information_schema.TABLES where table_schema='%s' and table_name = '%s'"%(dbname,tablename)

        try:
            cursor.execute(sql)
            results = cursor.fetchall() #接受全部返回行
        except:
            #不存在这张表返回错误提示
            raise Exception('This table does not exist')
        if not results:
            return None
        else:
            return results

    """datas = {(key: value),.....}"""
    def insert_mysql_with_json(self, tablename, datas):
        keys = datas[0].keys()
        keys = str(tuple(keys))
        keys = ''.join(keys.split("'")) # 用' 隔开
        print(keys)
        ret = []
        for dt in datas:
            values = dt.values() ##  ‘str' object has no attribute#
            sql = "insert into %s" % tablename + keys
            sql = sql + " values" + str(tuple(values))
            ret.append(sql)
        self.insert_into_sql(ret)

    def insert_into_sql(self,sqls):
        cursor = self.db.cursor()
        for sql in sqls:
            # 执行sql语句
            try:
                cursor.execute(sql)
                self.db.commit()
            except:
                self.db.rollback()

    """找列名"""
    def find_columns(self, tablename):
        sql = "select COLUMN_NAME from information_schema.columns where table_name='%s'" % tablename
        cursor = self.db.cursor()
        try:
            cursor.execute(sql)
            results = cursor.fetchall()
        except:
            raise Exception('find columns fail.')
        return tuple(map(lambda x: x[0], results))

    def find_rows(self, tablename, condition, fieldName=None):
        """
        :param tablename: test_scale1015
        :param condition: transaction_hash = '.....'
        :param fieldName: None or (columns1010, columns1011, columns1012, columns1013, time)
        :return:
        """
        cursor = self.db.cursor()
        sql = ''
        if fieldName==None:
            fieldName = self.find_columns(tablename)
            sql = "select * from %s where %s" % (tablename, condition)
        else:
            fieldNameStr = ','.join(fieldName)
            sql = "select %s from %s where %s" % (fieldNameStr, tablename, condition)
            
        try:
            cursor.execute(sql)
            results = cursor.fetchall()
        except:
            raise Exception('find fail.')
        return results

class POLLING_EVENTS(object):
    def __init__(self):
        self.blockchain_proxy = dict()
        self.polling_events = dict()
        self.polling_events_contract_proxy_cache = dict()

        self.polling_delay = 3
        self.polled_blocknumber = 0
        self.is_stopped = False
        self.DBService = DBService()

    def update_polling_event(self):
        reload(custom_contract_events)
        for key in custom_contract_events.__pollingEventSet__ : 
            chain_name,contract_name,event_name = key.split('_')[:3]
            self.polling_events[chain_name] = dict()
            self.polling_events[chain_name][contract_name] = dict()
            self.polling_events[chain_name][contract_name][event_name] = dict()
            self.polling_events[chain_name][contract_name][event_name]["filter_args"] = custom_contract_events.__pollingEventSet__[key]['filter_args']

            key = chain_name + '_' + contract_name
            if self.polling_events_contract_proxy_cache.get(key) == None:
                self.polling_events_contract_proxy_cache[key] = self.blockchain_proxy[chain_name].attach_contract(contract_name)

    
    def run(self,chain_name,_proxy):
        print('[CHAIN {}]satrt polling contract event...'.format(chain_name))
        self.blockchain_proxy[chain_name] = _proxy

        while not self.is_stopped:
            gevent.sleep(self.polling_delay)
            print('@@@@@@@@ CHAIN [{}] tick {}.----------------------------'.format(chain_name,time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))))
            self.update_polling_event()
           
            if chain_name in self.polling_events.keys() : 

                chain_proxy = self.blockchain_proxy[chain_name]
                polling_current_blocknumber = chain_proxy.block_number()
                
                for contract_name in self.polling_events[chain_name] :
                    contract_proxy = self.polling_events_contract_proxy_cache.get(chain_name + '_' + contract_name)
                    if contract_proxy == None:
                        print('@@@@@@@@ CHAIN [{}] contract [{}] has no proxy.'.format(chain_name,contract_name))
                        continue

                    for event_name in self.polling_events[chain_name][contract_name] :
                        event_key, event = contract_proxy.poll_contract_event(
                            self.polled_blocknumber,
                            event_name,
                            0,False,
                            self.polling_events[chain_name][contract_name][event_name]["filter_args"]
                        )
                        DBcallback = self.DBService.polling_events_callback[chain_name + '_' + contract_name + '_' + event_name]
                        sql_sets = self.polling_events[chain_name][contract_name][event_name]['stage']
                        DBcallback(sql_sets,event['transaction_hash'],(event))
                        
                self.polled_blocknumber = polling_current_blocknumber

    def stop(self):
        self.is_stopped = True

class PYETHAPI_ATMCHAIN(PYETHAPI):

    def __init__(self,blockchain_service):
        print('init PYETHAPI_ATMCHAIN ...')
        super(PYETHAPI_ATMCHAIN, self).__init__(blockchain_service)
        self.polling_events = POLLING_EVENTS()
    
    def new_blockchain_proxy(self, chain_name,endpoint,keystore_path):
        _proxy = super(PYETHAPI_ATMCHAIN, self).new_blockchain_proxy(chain_name,endpoint,keystore_path)
        polling = Greenlet.spawn(
            self.polling_events.run,
            chain_name,
            _proxy,
        ) 
        return _proxy

    def ATM_accounts_list(self): 
        contract_Addresses=dict()
        ethereum_proxy = self._get_chain_proxy('ethereum')
        atmchain_proxy = self._get_chain_proxy('atmchain')
        ERC20Token_ethereum_address = self._get_contract_address(
            'ethereum',
            'ATMToken',
            )
        TokenExchange_ethereum_address = self._get_contract_address(
            'ethereum',
            'TokenExchange',
            )
        ERC223Token_atmchain_address = self._get_contract_address(
            'atmchain',
            'ERC223Token',
            )
        contract_Addresses['ATMToken_address'] = address_encoder(ERC20Token_ethereum_address) if ERC20Token_ethereum_address != None else 'NOT deployed'
        contract_Addresses['TokenExchange_address'] = address_encoder(TokenExchange_ethereum_address) if TokenExchange_ethereum_address != None else 'NOT deployed'
        contract_Addresses['ERC223Token_address'] = address_encoder(ERC223Token_atmchain_address) if ERC223Token_atmchain_address != None else 'NOT deployed'

        return contract_Addresses,self.eth_accounts_list('ethereum'),self.eth_accounts_list('atmchain')

    def deploy_ATM_contract(self,atm_address=None): 
        
        ethereum_proxy = self._get_chain_proxy('ethereum')
        ethereum_sender = ethereum_proxy.account_manager.admin_account
        atmchain_proxy = self._get_chain_proxy('atmchain')
        atmchain_sender = atmchain_proxy.account_manager.admin_account

        ERC223Token_atmchain_owner = atmchain_proxy.deploy_contract( 
            atmchain_sender,
            'ERC223Token.sol', 'ERC223Token',
            (100000,'REX',8,'REX Token'),
            )

        if atm_address == None:
            ERC20Token_ethereum_owner = ethereum_proxy.deploy_contract( 
                ethereum_sender,
                'ATMToken.sol', 'ATMToken',
                )
            atm_address = ERC20Token_ethereum_owner.address
        else:
            ethereum_proxy = self._get_chain_proxy('ethereum')
            ERC20Token_ethereum_owner = ethereum_proxy.attach_contract(
                'ATMToken.sol','ATMToken',
                contract_address=atm_address,
                attacher=ethereum_sender,
                )

        TokenExchange_ethereum_owner = ethereum_proxy.deploy_contract( 
            ethereum_sender, 
            'TokenExchange.sol', 'TokenExchange',
            (hexlify(atm_address),)
            )


    """
    def lock_ATM(self,from_chain,to_chain,advertiser,lock_amount):
        
        ethereum_proxy = self._get_chain_proxy(from_chain)
        atmchain_proxy = self._get_chain_proxy(to_chain)

        ERC20Token_ethereum_owner = ethereum_proxy.attach_contract(
            'ATMToken',
            attacher=ethereum_proxy.account_manager.admin_account,
            )
        TokenExchange_ethereum_owner = ethereum_proxy.attach_contract(
            'TokenExchange',
            attacher=ethereum_proxy.account_manager.admin_account,
            )
        ERC20Token_ethereum_advister = ethereum_proxy.attach_contract(
            'ATMToken',
            attacher=advertiser,
            )
        ERC223Token_atmchain_owner = atmchain_proxy.attach_contract(
            'ERC223Token',
            attacher=ethereum_proxy.account_manager.admin_account,
            )
        block_number = ethereum_proxy.block_number()
        txhash = ERC20Token_ethereum_advister.transfer(
            TokenExchange_ethereum_owner.address,lock_amount*constant.ATM_DECIMALS)
        ethereum_proxy.poll_contarct_transaction_result(
            txhash,block_number,ERC20Token_ethereum_advister,'Transfer',TokenExchange_ethereum_owner.address)

        block_number = ethereum_proxy.block_number()
        txhash = TokenExchange_ethereum_owner.lockToken(
            normalize_address(advertiser),lock_amount*constant.ATM_DECIMALS)
        ethereum_proxy.poll_contarct_transaction_result(
            txhash,block_number,TokenExchange_ethereum_owner,'LogLockToken',advertiser)

        block_number = atmchain_proxy.block_number()
        txhash = ERC223Token_atmchain_owner.mint(advertiser,lock_amount)
        atmchain_proxy.poll_contarct_transaction_result(
            txhash,block_number,ERC223Token_atmchain_owner,'Minted',advertiser) 

    def settle_ATM(self,from_chain,to_chain,scaner,settle_amount):
        
        ethereum_proxy = self._get_chain_proxy(from_chain)
        atmchain_proxy = self._get_chain_proxy(to_chain)

        ERC223Token_atmchain_owner = atmchain_proxy.attach_contract(
            'ERC223Token',
            attacher=ethereum_proxy.account_manager.admin_account,
            )

        if settle_amount > ERC223Token_atmchain_owner.balanceOf(scaner)/constant.ATM_DECIMALS:
            raise ValueError('insufficient token balance of {}'.format(scaner))

        ERC223Token_atmchain_scaner = atmchain_proxy.attach_contract(
            'ERC223Token',
            attacher=scaner,
            )
        TokenExchange_ethereum_owner = ethereum_proxy.attach_contract(
            'TokenExchange',
            attacher=ethereum_proxy.account_manager.admin_account,
            )

        block_number = atmchain_proxy.block_number()
        txhash = ERC223Token_atmchain_scaner.transfer(
            constant.BLACKHOLE_ADDRESS,settle_amount*constant.ATM_DECIMALS,'')
        atmchain_proxy.poll_contarct_transaction_result(
            txhash,block_number,ERC223Token_atmchain_scaner,'Transfer',scaner,constant.BLACKHOLE_ADDRESS)

        block_number = ethereum_proxy.block_number()
        txhash = TokenExchange_ethereum_owner.settleToken(scaner,settle_amount*constant.ATM_DECIMALS)
        ethereum_proxy.poll_contarct_transaction_result(txhash,block_number,TokenExchange_ethereum_owner,'LogSettleToken',scaner)
    """

    def query_currency_balance(self,chain_name,account):
        _proxy = self._get_chain_proxy(chain_name)

        temp = _proxy.balance(address_decoder(account))
        result = float(temp)/constant.WEI_TO_ETH
        return result

    def query_atmchain_balance(self,src_chain,dest_chain,account):

        result=dict()
        ethereum_proxy = self._get_chain_proxy(src_chain)
        atmchain_proxy = self._get_chain_proxy(dest_chain)

        ERC20Token_ethereum = ethereum_proxy.attach_contract(
            'ATMToken'
            )

        ERC223Token_atmchain = atmchain_proxy.attach_contract(
            'ERC223Token'
            )

        temp = ethereum_proxy.balance(address_decoder(account))
        result['ETH balance in ethereum'] = float(temp)/constant.WEI_TO_ETH

        temp = ERC20Token_ethereum.balanceOf(account) if ERC20Token_ethereum != None else 0
        result['ATM balance in ethereum'] = float(temp)/constant.ATM_DECIMALS 
    
        temp = atmchain_proxy.balance(address_decoder(account))
        result['ETH balance in atmchain'] = float(temp)/constant.WEI_TO_ETH
        
        temp = ERC223Token_atmchain.balanceOf(account) if ERC223Token_atmchain != None else 0
        result['ATM balance in atmchain'] = float(temp)/constant.ATM_DECIMALS
    
        return result
