# -*- coding: utf-8 -*-
import os
import pymysql
from ethereum.utils import normalize_address
from binascii import hexlify, unhexlify
from service.utils import (
    address_encoder,
    address_decoder,
)
import threading
import click
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
        _proxy.account_manager.set_admin_account(old_address,admin_address)

    def get_admin_account(self,chain_name):
        _proxy = self._get_chain_proxy(chain_name)
        return _proxy.account_manager.get_admin_account()

    def set_admin_password(self,chain_name,pwd):
        _proxy = self._get_chain_proxy(chain_name)
        _proxy.account_manager.set_admin_password(pwd)
    def get_admin_password(self,chain_name):
        _proxy = self._get_chain_proxy(chain_name)
        return _proxy.account_manager.get_admin_password()

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
        password = click.prompt('Password to transfer currency coin', default='', hide_input=True,
                                confirmation_prompt=False, show_default=False)
        _proxy = self._get_chain_proxy(chain_name)
        #amount = amount * constant.WEI_TO_ETH
        transaction_hash_hex = _proxy.transfer_currency(sender, to, amount, password=password)
        _proxy.poll_contarct_transaction_result(transaction_hash_hex)
    
    """token转账"""
    def transfer_token(self,chain_name,contract_address,sender,to,amount,is_erc223=False):
        password = click.prompt('Password to unlock {}'.format(sender), default='', hide_input=True,
                                confirmation_prompt=False, show_default=False)
        _proxy = self._get_chain_proxy(chain_name)
        if contract_address[:2] == "0x":
            contract_address = contract_address[2:]
        if sender[:2] == "0x":
            sender = sender[2:]
        contract_proxy = _proxy.attach_contract(
            'ATMToken',
            contract_file='ATMToken.sol',
            contract_address=unhexlify(contract_address),
            attacher=sender,
            password=password,
        )
        block_number = _proxy.block_number()
        #由于pythpn版本以太坊暂时无法处理同名函数, 暂时通过flag来区分
        if is_erc223 == True:
            txhash = contract_proxy.transfer(to,amount*constant.ATM_DECIMALS,'')
        else:
            txhash = contract_proxy.transfer(to,amount*constant.ATM_DECIMALS)

        _proxy.poll_contarct_transaction_result(txhash,block_number,contract_proxy,'Transfer',to)
        _proxy.account_manager.get_account(sender,password).lock()

    def get_nonce(self,chain_name,user):
        if chain_name == None or chain_name=='':
            chain_name = 'ethereum'
        _proxy = self._get_chain_proxy(chain_name)
        nonce = _proxy.nonce(user)
        return nonce

    def get_deposit_limit(self):
        return custom_contract_events.__BridgeConfig__['limit']

    def get_balance(self,chain_name,user):
        if chain_name ==None or chain_name=='':
            chain_name = 'ethereum'
        _proxy = self._get_chain_proxy(chain_name)
        nonce = _proxy.nonce(user)
        return nonce

class DBService(object):

    def __init__(self):
        self.db = None
        self.lock = threading.Lock()
        self.is_DEPOSIT_table_exist = False
        self.polling_events_callback = dict()
        self.polling_events_callback['ethereum_ATMToken_Transfer'] = self.ethereum_ATMToken_Transfer_to_DB
        self.polling_events_callback['atmchain_ForeignBridge_Deposit'] = self.atmchain_ForeignBridge_Deposit_to_DB

    def ethereum_ATMToken_Transfer_offline_to_DB(self,sql):
        self.insert_into_sql([sql])
  
    def ethereum_ATMToken_Transfer_to_DB(self, sql_sets, tx_hash, *args):
        """检查tx_hash对应记录数据是否存在"""
        condition = "TRANSACTION_HASH_SRC = '%s'"%(tx_hash)
        result = self.find_rows('DEPOSIT',condition)
        if result == None:
            print('not found table DEPOSIT')
            return
        if result == tuple():   #没有记录， 插入该记录
            sql = sql_sets[1](*args)
        elif result[0][3] == 1:      #已有记录，并且处于stage 1， 更新该记录
            sql = sql_sets[0](*args)
        else:
            print('hash:{} is already in stage {}'.format(tx_hash,result[0][3]))
            return
        self.insert_into_sql([sql])


    def atmchain_ForeignBridge_Deposit_to_DB(self, sql_sets, tx_hash, *args):
        
        """检查数据库bridge中是否存在DEPOSIT表， 如果不存在，新建该表"""
        result = self.find_rows('DEPOSIT',"STAGE = '3'") #and TRANSACTION_HASH_DEST = '{}'
        for rec in result:
            if rec[8] == tx_hash:
                return
        sql = sql_sets[0](*args)
        self.insert_into_sql([sql])

    def connect(self):
        self.db = pymysql.connect(**custom_contract_events.__DBConfig__)
        
        exsist = False
        cursor = self.db.cursor()
        try:
            # 执行sql语句
            cursor.execute('show databases')
            rows = cursor.fetchall()
            for row in rows:
                if custom_contract_events.__DBConfig__['db'] in row:
                    exsist = True
            if exsist == False:
                cursor.execute('create database if not exists ' + custom_contract_events.__DBConfig__['db'])
                # 提交到数据库执行
                self.db.commit()
        except:
            self.db.rollback()

        print("connect mysql ok. db is {} ".format(custom_contract_events.__DBConfig__['db']))
        """
        if self.is_table_exist(custom_contract_events.__DBConfig__['db'], 'DEPOSIT') == False:
            fields = "ID INT AUTO_INCREMENT,\
                        USER_ADDRESS  CHAR(42) NOT NULL, \
                        AMOUNT BIGINT, \
                        STAGE INT NOT NULL, \
                        CHAIN_NAME_SRC  CHAR(20), \
                        TRANSACTION_HASH_SRC CHAR(255) NOT NULL, \
                        BLOCK_NUMBER_SRC INT, \
                        CHAIN_NAME_DEST  CHAR(20), \
                        TRANSACTION_HASH_DEST CHAR(255), \
                        BLOCK_NUMBER_DEST INT,\
                        TIME_STAMP CHAR(32), \
                        PRIMARY KEY (ID,TRANSACTION_HASH_SRC)"
            self.create_table('DEPOSIT', fields)
        """
    def disconnect(self):
        self.db.close()

    def create_table(self, tablename, columns):

        cursor = self.db.cursor()
        sql="create table %s("%(tablename,)
        sql+=columns+')'
        try:
            cursor.execute(sql)
            print("Table %s is created"%tablename)
            self.db.commit()
        except:
            self.db.rollback()

    def is_table_exist(self, dbname, tablename):
        if tablename == 'DEPOSIT' and self.is_DEPOSIT_table_exist == True:
            return True
            
        cursor=self.db.cursor()
        sql="select table_name from information_schema.TABLES where table_schema='%s' and table_name = '%s'"%(dbname,tablename)
        try:
            cursor.execute(sql)
            results = cursor.fetchall() #接受全部返回行
            self.db.commit()
        except Exception,e:
            #不存在这张表返回错误提示
            print('query db {} table {} fail:{}'.format(dbname,tablename,e.message))
            return False
        if not results:
            return False
        else:
            if tablename == 'DEPOSIT':
                self.is_DEPOSIT_table_exist = True
            return True

    """datas = {(key: value),.....}
    def insert_mysql_with_json(self, tablename, datas):
        keys = datas[0].keys()
        keys = str(tuple(keys))
        keys = ''.join(keys.split("'")) # 用' 隔开
        ret = []
        for dt in datas:
            values = dt.values() ##  ‘str' object has no attribute#
            sql = "insert into %s" % tablename + keys
            sql = sql + " values" + str(tuple(values))
            ret.append(sql)
        self.insert_into_sql(ret)
    """
    def insert_into_sql(self,sqls):
        cursor = self.db.cursor()
        for sql in sqls:
            # 执行sql语句
            try:
                self.lock.acquire()
                #print('DEBUG: ',sql)
                cursor.execute(sql)
                self.lock.release()
                self.db.commit()
            except Exception,e:
                print('insert sql <<{}>> fail:{}'.format(sql,e.message))
                self.db.rollback()
                self.lock.release()

    """获取指定table的所有列的名字
    def find_columns(self, tablename):
        sql = "select COLUMN_NAME from information_schema.columns where table_name='%s'" % tablename
        cursor = self.db.cursor()
        try:
            self.lock.acquire()
            cursor.execute(sql)
            self.lock.release()
            self.db.commit()
            results = cursor.fetchall()
        except:
            self.lock.release()
            return tuple()
        return tuple(map(lambda x: x[0], results))
    """
    def find_rows(self, tablename, condition, fieldName=None):
        """
        :param tablename: test_scale1015
        :param condition: transaction_hash = '.....'
        :param fieldName: None or (columns1010, columns1011, columns1012, columns1013, time)
        :return:
        """
        
        sql = ''
        if fieldName==None:
            #fieldName = self.find_columns(tablename)
            sql = "select * from %s where %s" % (tablename, condition)
        else:
            fieldNameStr = ','.join(fieldName)
            sql = "select %s from %s where %s" % (fieldNameStr, tablename, condition)
        
        db_for_find_rows = pymysql.connect(**custom_contract_events.__DBConfig__)    
        try:
            cursor = db_for_find_rows.cursor()
            cursor.execute(sql)
            results = cursor.fetchall()
        except:
            db_for_find_rows.close()
            return tuple()
        db_for_find_rows.close()
        return results


class ATM_DEPOSIT_WORKER(object):
    def __init__(self):
        self.current_blockchain_proxy = dict()
        self.current_connected_chain = list()
        self.query_delay = 3
        self.current_query_id = 0
        self.is_stopped = False
        self.DBService = DBService()

    def add_new_chain(self,chain_name,_proxy):
        self.current_connected_chain.append(chain_name)
        self.current_blockchain_proxy[chain_name] = _proxy

    def run(self):
        while not self.is_stopped:
            gevent.sleep(self.query_delay)
            result = self.DBService.find_rows('DEPOSIT',"STAGE = '2' AND CHAIN_NAME_DEST not in ('atmchain')")
            if result == None:
                continue 
            if result == tuple():   
                #print('step idle2')
                continue
            else:                   #已有记录，更新该记录
                sqls = ["UPDATE DEPOSIT SET CHAIN_NAME_DEST = '%s' WHERE TRANSACTION_HASH_SRC = '%s'" % ('atmchain', record[5]) for record in result]
                self.DBService.insert_into_sql(sqls)
                for record in result:
                    self.deposit(record[1], record[2], record[5])

    def deposit(self, recipient, value, tx_hash_src):
        value = value * (10**10)
        print("deposit {} to {} for transaction_hash:{}".format(value, recipient, tx_hash_src))
        _proxy = self.current_blockchain_proxy['atmchain']
        admin_account = _proxy.account_manager.get_admin_account()
        contract_proxy = _proxy.attach_contract(
            'ForeignBridge',
            contract_file=custom_contract_events.__contractInfo__['ForeignBridge']['file'],
            contract_address=unhexlify(custom_contract_events.__contractInfo__['ForeignBridge']['address']),
            attacher=admin_account,
            password=_proxy.account_manager.get_admin_password(),
        )
        txhash = contract_proxy.deposit('0x'+recipient,value,unhexlify(tx_hash_src[2:]),value=value)
        _proxy.poll_contarct_transaction_result(txhash)

    def deposit_manual(self,id):
        result = self.DBService.find_rows('DEPOSIT',"STAGE = '2' AND CHAIN_NAME_DEST = 'atmchain' AND ID < '{}'".format(id))
        if result == None or result == tuple():
            return
        else:
            for record in result:
                self.deposit(record[1], record[2], record[5])

    def deposit_status(self,user,tx_hash):
        if user[:2] == '0x':
            user = user[2:]
        if tx_hash != None and tx_hash[:2] != '0x':
            print("transaction hash must be start with '0x'.")
            return list()
        if tx_hash == None or tx_hash == "":
            result = self.DBService.find_rows('DEPOSIT',"USER_ADDRESS = '{}'".format(user))
        else:
            result = self.DBService.find_rows('DEPOSIT',"TRANSACTION_HASH_SRC = '{}'".format(tx_hash))
        return result

    def stop(self):
        self.is_stopped = True
        self.DBService.disconnect()

class LISTEN_CONTRACT_EVENTS_TASK(object):
    def __init__(self):
        self.current_blockchain_proxy = dict()
        self.current_connected_chain = list()
        self.polling_events = dict()
        self.polling_events_contract_proxy_cache = dict()

        self.polling_delay = 3
        self.polled_blocknumber = dict()
        self.is_stopped = False
        self.DBService = DBService()

    def add_new_chain(self,chain_name,_proxy):
        self.current_connected_chain.append(chain_name)
        self.current_blockchain_proxy[chain_name] = _proxy
        self.polled_blocknumber[chain_name] = 0

    def update_polling_event(self):
        reload(custom_contract_events)
        for key in custom_contract_events.__pollingEventSet__ : 
            chain_name,contract_name,event_name = key.split('_')[:3]
            if chain_name in self.current_connected_chain:
                self.polling_events[chain_name] = dict()
                self.polling_events[chain_name][contract_name] = dict()
                self.polling_events[chain_name][contract_name][event_name] = custom_contract_events.__pollingEventSet__[key]

            key = chain_name + '_' + contract_name
            if self.polling_events_contract_proxy_cache.get(key) == None and \
                custom_contract_events.__contractInfo__[contract_name]['address']!="":

                self.polling_events_contract_proxy_cache[key] = \
                    self.current_blockchain_proxy[chain_name].attach_contract(
                    contract_name,
                    contract_file=custom_contract_events.__contractInfo__[contract_name]['file'], 
                    contract_address=unhexlify(custom_contract_events.__contractInfo__[contract_name]['address']),)
    
    def run(self):
        while not self.is_stopped:
            gevent.sleep(self.polling_delay)
            self.update_polling_event()
           
            for chain_name in self.polling_events.keys() : 

                chain_proxy = self.current_blockchain_proxy[chain_name]
                polling_current_blocknumber = chain_proxy.block_number()
                
                for contract_name in self.polling_events[chain_name] :
                    contract_proxy = self.polling_events_contract_proxy_cache.get(chain_name + '_' + contract_name)
                    if contract_proxy == None:
                        print('@@@@@@@@ CHAIN [{}] contract [{}] has no proxy.'.format(chain_name,contract_name))
                        continue

                    for event_name in self.polling_events[chain_name][contract_name] :
                        event_key, events = contract_proxy.poll_contract_event(
                            self.polled_blocknumber[chain_name],
                            event_name,
                            0,False,
                            *self.polling_events[chain_name][contract_name][event_name]["filter_args"]
                        )
                        if events == list():
                            print('step idle ',event_name)
                            continue
                        for event in events:
                            print('CHAIN: {} catched event: {}. block: {} hash:{}'.format(chain_name,event_name,event['block_number'],event['transaction_hash']))
                            DBcallback = self.DBService.polling_events_callback[chain_name + '_' + contract_name + '_' + event_name]
                            sql_sets = self.polling_events[chain_name][contract_name][event_name]['stage']
                            DBcallback(sql_sets,event['transaction_hash'],(event))
                        
                self.polled_blocknumber[chain_name] = polling_current_blocknumber

    def stop(self):
        self.is_stopped = True
        self.DBService.disconnect()

class PYETHAPI_ATMCHAIN(PYETHAPI):

    def __init__(self,blockchain_service):
        print('init PYETHAPI_ATMCHAIN ...')
        super(PYETHAPI_ATMCHAIN, self).__init__(blockchain_service)
        self.listen_contract_events = LISTEN_CONTRACT_EVENTS_TASK()
        self.listen_contract_events.DBService.connect()
        polling = Greenlet.spawn(
            self.listen_contract_events.run,
        ) 
        self.atm_deposit_worker = ATM_DEPOSIT_WORKER()
        self.atm_deposit_worker.DBService.connect()
        polling = Greenlet.spawn(
            self.atm_deposit_worker.run,
        ) 
    
    def new_blockchain_proxy(self, chain_name,endpoint,keystore_path):
        _proxy = super(PYETHAPI_ATMCHAIN, self).new_blockchain_proxy(chain_name,endpoint,keystore_path)
        self.listen_contract_events.add_new_chain(chain_name,_proxy)
        self.atm_deposit_worker.add_new_chain(chain_name,_proxy)
        return _proxy

    def deposit_atm_manual(self,id):
        self.atm_deposit_worker.deposit_manual(id)

    def query_atm_deposit_status(self,user,tx_hash):
        return self.atm_deposit_worker.deposit_status(user,tx_hash)

    """执行离线交易"""
    def send_raw_transaction(self,chain_name,signed_data):
        _proxy = self._get_chain_proxy(chain_name)
        transaction_hash = _proxy.sendRawTransaction(signed_data)
        #过滤向homebridge转atm token的离线交易
        if transaction_hash !='' and signed_data[76:84] == 'a9059cbb' and signed_data[108:148] == custom_contract_events.__contractInfo__['HomeBridge']['address']:
            sql = custom_contract_events.ATM_Deposit1_insert_DBtable('0x'+transaction_hash)
            self.atm_deposit_worker.DBService.ethereum_ATMToken_Transfer_offline_to_DB(sql)
        return transaction_hash

    def query_currency_balance(self,chain_name,account):
        _proxy = self._get_chain_proxy(chain_name)

        temp = _proxy.balance(address_decoder(account))
        
        return temp

    def query_atmchain_balance(self,src_chain,dest_chain,account):

        result=dict()
        ethereum_proxy = self._get_chain_proxy(src_chain)

        ERC20Token_ethereum = ethereum_proxy.attach_contract(
                    'ATMToken',
                    contract_file=custom_contract_events.__contractInfo__['ATMToken']['file'], 
                    contract_address=unhexlify(custom_contract_events.__contractInfo__['ATMToken']['address']),)

        if ERC20Token_ethereum == None:
            return result
        temp = self.query_currency_balance(src_chain, account)
        result['ETH_balance'] = temp

        temp = ERC20Token_ethereum.balanceOf(account) if ERC20Token_ethereum != None else 0
        result['ATM_balance_ethereum'] = temp
    
        temp = self.query_currency_balance(dest_chain, account)
        result['ATM_balance_atmchain'] = temp
    
        return result
