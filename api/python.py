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
from ethereum import slogging
log = slogging.get_logger('root')

class PYETHAPI(object):
    """ CLI interface. """

    def __init__(self,blockchain_service):
        print('init pyeth-api ...')
        self.blockchain_service = blockchain_service

    def set_log_level(self,level):
        root = slogging.get_logger("root")
        root.setLevel(level)
        print('log name:{} level:{}'.format(root.name,level))
        
    def _get_chain_proxy(self,chain_name):
        assert chain_name in self.blockchain_service.blockchain_proxy.keys()
        _proxy = self.blockchain_service.blockchain_proxy[chain_name]
        return _proxy

    def _get_contract_address(self,chain_name,contract_name): 
        _proxy = self._get_chain_proxy(chain_name)
        _contract_proxy = _proxy.attach_contract(contract_name)
        return _contract_proxy.address if _contract_proxy != None else None


    """新建区块链代理"""
    def new_blockchain_proxy(self, chain_name,endpoint,keystore_path,admin_account=None):
        assert keystore_path != None
        if chain_name not in self.blockchain_service.blockchain_proxy.keys():
            _proxy = self.blockchain_service.newBlockchainProxy(
                chain_name, endpoint, keystore_path,admin_account)
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

        transaction_hash_hex = _proxy.transfer_currency(chain_name,sender, to, amount, password=password)
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
            txhash = contract_proxy.transfer(to,amount,'')
        else:
            txhash = contract_proxy.transfer(to,amount)

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
        self.lock = threading.Lock()
        self.polling_events_callback = dict()
        self.polling_events_callback['ethereum_ATMToken_Transfer'] = self.ethereum_ATMToken_Transfer_to_DB
        self.polling_events_callback['atmchain_ForeignBridge_Deposit'] = self.atmchain_ForeignBridge_Deposit_to_DB
        self.polling_events_callback['atmchain_ForeignBridge_TransferBack'] = self.atmchain_ForeignBridge_TransferBack_to_DB
        self.polling_events_callback['ethereum_HomeBridge_Withdraw'] = self.ethereum_HomeBridge_Withdraw_to_DB

    def ethereum_ATMToken_Transfer_offline_to_DB(self,db,sql):
        self.insert_into_sql(db, [sql])
  
    def ethereum_ATMToken_Transfer_to_DB(self, db, sql_sets, tx_hash, *args):
        """检查tx_hash对应记录数据是否存在"""
        condition = "TRANSACTION_HASH_SRC = '%s'"%(tx_hash)
        result = self.find_rows(db,'DEPOSIT',condition)
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
        self.insert_into_sql(db, [sql])


    def atmchain_ForeignBridge_Deposit_to_DB(self, db, sql_sets, tx_hash, *args):
        result = self.find_rows(db,'DEPOSIT',"STAGE = '3'") #and TRANSACTION_HASH_DEST = '{}'
        for rec in result:
            if rec[8] == tx_hash:
                return
        sql = sql_sets[0](*args)
        self.insert_into_sql(db, [sql])

    def atmchain_ForeignBridge_TransferBack_to_DB(self, db, sql_sets, tx_hash, *args):
        """检查tx_hash对应记录数据是否存在"""
        condition = "TRANSACTION_HASH_SRC = '%s'"%(tx_hash)
        result = self.find_rows(db,'WITHDRAW',condition)
        if result == None:
            log.error('not found table WITHDRAW')
            return
        if result == tuple():   #没有记录， 插入该记录
            sql = sql_sets[1](*args)
            
        elif result[0][3] == 1:      #已有记录，并且处于stage 1， 更新该记录
            sql = sql_sets[0](*args)
        else:
            log.info('hash:{} is already in stage {}'.format(tx_hash,result[0][3]))
            return
        self.insert_into_sql(db, [sql])

    def ethereum_HomeBridge_Withdraw_to_DB(self, db, sql_sets, tx_hash, *args):
        result = self.find_rows(db,'WITHDRAW',"STAGE = '3'") #and TRANSACTION_HASH_DEST = '{}'
        for rec in result:
            if rec[8] == tx_hash:
                return
        sql = sql_sets[0](*args)
        self.insert_into_sql(db, [sql])

    def init_db(self):
        db = pymysql.connect(**custom_contract_events.__DBConfig__)
        
        exsist = False
        cursor = db.cursor()
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
                db.commit()
        except:
            db.rollback()

        print("connect mysql ok. db is {} ".format(custom_contract_events.__DBConfig__['db']))
        
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

        if self.is_table_exist(db,custom_contract_events.__DBConfig__['db'], 'DEPOSIT') == False:
            print("create_table DEPOSIT ... ")
            self.create_table(db,'DEPOSIT', fields)
        if self.is_table_exist(db,custom_contract_events.__DBConfig__['db'], 'WITHDRAW') == False:
            print("create_table DEPOSIT ... ")
            self.create_table(db,'WITHDRAW', fields)
        db.close()

    def create_table(self, db, tablename, columns):

        cursor = db.cursor()
        sql="create table %s("%(tablename,)
        sql+=columns+')'
        try:
            cursor.execute(sql)
            print("Table %s is created"%tablename)
            db.commit()
        except:
            db.rollback()

    def is_table_exist(self, db, dbname, tablename):
        cursor=db.cursor()
        sql="select table_name from information_schema.TABLES where table_schema='%s' and table_name = '%s'"%(dbname,tablename)
        try:
            cursor.execute(sql)
            results = cursor.fetchall() #接受全部返回行
            db.commit()
        except Exception,e:
            #不存在这张表返回错误提示
            print('query db {} table {} fail:{}'.format(dbname,tablename,e.message))
            return False
        if not results:
            print('query db {} table {} not exsit'.format(dbname,tablename))
            return False
        else:
            print('query db {} table {} exsit:{}'.format(dbname,tablename,results))
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
    def insert_into_sql(self,db,sqls):
        cursor = db.cursor()
        for sql in sqls:
            # 执行sql语句
            try:
                cursor.execute(sql)
                db.commit()
            except Exception,e:
                print('insert sql <<{}>> fail:{}'.format(sql,e.message))
                db.rollback()

    def find_rows(self, db, tablename, condition, fieldName=None):
        sql = ''

        cursor = db.cursor()
        if fieldName==None:
            #fieldName = self.find_columns(tablename)
            sql = "select * from %s where %s" % (tablename, condition)
        else:
            fieldNameStr = ','.join(fieldName)
            sql = "select %s from %s where %s" % (fieldNameStr, tablename, condition)
        try:
            log.debug('find rows: {}'.format(sql))
            cursor.execute(sql)
            results = cursor.fetchall()
        except:
            return tuple()
        return results

    def new_db_connect(self):
        return pymysql.connect(**custom_contract_events.__DBConfig__) 

    def db_close(self, db):
        db.close()

class ATM_BRIDGE_WORKER(object):
    def __init__(self):
        self.current_blockchain_proxy = dict()
        self.current_connected_chain = list()
        self.query_delay = 3
        self.current_query_id = 0
        self.is_stopped = False
        self.DBService = DBService()
        self.DBService.init_db()

    def add_new_chain(self,chain_name,_proxy):
        self.current_connected_chain.append(chain_name)
        self.current_blockchain_proxy[chain_name] = _proxy

    def run_deposit_loop(self):
        db = self.DBService.new_db_connect()
        while not self.is_stopped:
            gevent.sleep(self.query_delay)
            result = self.DBService.find_rows(db,'DEPOSIT',"STAGE = '2' and CHAIN_NAME_DEST not in ('atmchain')")
            if result == None or result == tuple():
                log.debug('step idle: run_deposit_loop')
                continue
            else:                   #已有记录，更新该记录
                sqls = ["UPDATE DEPOSIT SET CHAIN_NAME_DEST = '%s' WHERE TRANSACTION_HASH_SRC = '%s'" % ('atmchain', record[5]) for record in result]
                self.DBService.insert_into_sql(db,sqls)
                for record in result:
                    self.deposit(record[1], record[2], record[5])

        self.DBService.db_close(db)

    def run_withdraw_loop(self):
        db = self.DBService.new_db_connect()
        while not self.is_stopped:
            gevent.sleep(self.query_delay)
            result = self.DBService.find_rows(db,'WITHDRAW',"STAGE = '2' AND CHAIN_NAME_DEST not in ('ethereum')")
            if result == None:
                continue 
            if result == tuple():   
                log.debug('step idle: run_withdraw_loop')
                continue
            else:                   #已有记录，更新该记录
                sqls = ["UPDATE WITHDRAW SET CHAIN_NAME_DEST = '%s' WHERE TRANSACTION_HASH_SRC = '%s'" % ('ethereum', record[5]) for record in result]
                self.DBService.insert_into_sql(db,sqls)
                for record in result:
                    self.withdraw(record[1], record[2], record[5])

        self.DBService.db_close(db)

    def deposit(self, recipient, value, tx_hash_src):
        value = value * (10**10)
        _proxy = self.current_blockchain_proxy['atmchain']
        admin_account = _proxy.account_manager.get_admin_account()
        ban_required = _proxy.balance(address_decoder(admin_account))
        if int(ban_required) < value :
            log.critical("[atmchain]admin has insuffient ATM balance:{}. required:{}".format(ban_required,value))
            return
        contract_proxy = _proxy.attach_contract(
            'ForeignBridge',
            contract_file=custom_contract_events.__contractInfo__['ForeignBridge']['file'],
            contract_address=unhexlify(custom_contract_events.__contractInfo__['ForeignBridge']['address']),
            attacher=admin_account,
            password=_proxy.account_manager.get_admin_password(),
        )
        txhash = contract_proxy.deposit('0x'+recipient,value,unhexlify(tx_hash_src[2:]),value=value)
        _proxy.poll_contarct_transaction_result(txhash)
        log.info("\n--------\ndeposit {} to 0x{}\nsrc tx_hash: {}\ndest tx_hash: 0x{}\n--------\n".format(value, recipient, tx_hash_src,txhash))

    def withdraw(self, recipient, value, tx_hash_src):
        
        _proxy = self.current_blockchain_proxy['ethereum']
        admin_account = _proxy.account_manager.get_admin_account()
        ERC20Token_ethereum = _proxy.attach_contract(
                    'ATMToken',
                    contract_file=custom_contract_events.__contractInfo__['ATMToken']['file'], 
                    contract_address=unhexlify(custom_contract_events.__contractInfo__['ATMToken']['address']),)
        
        ban_required = ERC20Token_ethereum.balanceOf(custom_contract_events.__contractInfo__['HomeBridge']['address']) if ERC20Token_ethereum != None else 0
        if int(ban_required) < value :
            log.critical("[ethereum]admin has insuffient ATM token balance:{}. required:{}".format(ban_required,value))
            return
        
        contract_proxy = _proxy.attach_contract(
            'HomeBridge',
            contract_file=custom_contract_events.__contractInfo__['HomeBridge']['file'],
            contract_address=unhexlify(custom_contract_events.__contractInfo__['HomeBridge']['address']),
            attacher=admin_account,
            password=_proxy.account_manager.get_admin_password(),
        )
        txhash = contract_proxy.withdraw(custom_contract_events.__contractInfo__['ATMToken']['address'],'0x'+recipient,value,unhexlify(tx_hash_src[2:]))
        _proxy.poll_contarct_transaction_result(txhash)
        log.info("\n--------\nwithdraw {} to 0x{}\nsrc tx_hash: {}\ndest tx_hash: 0x{}\n--------\n".format(value, recipient, tx_hash_src,txhash))

    def deposit_manual(self,id):
        db = self.DBService.new_db_connect()
        result = self.DBService.find_rows(db, 'DEPOSIT',"STAGE = '2' AND CHAIN_NAME_DEST = 'atmchain' AND ID < '{}'".format(id))
        if result == None or result == tuple():
            return
        else:
            for record in result:
                self.deposit(record[1], record[2], record[5])
        self.DBService.db_close(db)

    def withdraw_manual(self,id):
        db = self.DBService.new_db_connect()
        result = self.DBService.find_rows(db, 'WITHDRAW',"STAGE = '2' AND CHAIN_NAME_DEST = 'ethereum' AND ID < '{}'".format(id))
        if result == None or result == tuple():
            return
        else:
            for record in result:
                self.withdraw(record[1], record[2], record[5])
        self.DBService.db_close(db)

    def query_bridge_status(self,bridge_type,user,tx_hash):
        db = self.DBService.new_db_connect()
        if user[:2] == '0x':
            user = user[2:]
        if tx_hash != None and tx_hash[:2] != '0x':
            print("transaction hash must be start with '0x'.")
            return list()
        if tx_hash == None or tx_hash == "":
            result = self.DBService.find_rows(db, bridge_type,"USER_ADDRESS = '{}'".format(user))
        else:
            result = self.DBService.find_rows(db, bridge_type,"TRANSACTION_HASH_SRC = '{}'".format(tx_hash))
        self.DBService.db_close(db)
        return result

    def deposit_status(self,user,tx_hash):
        return self.query_bridge_status('DEPOSIT',user,tx_hash)

    def withdraw_status(self,user,tx_hash):
        return self.query_bridge_status('WITHDRAW',user,tx_hash)

    def stop(self):
        self.is_stopped = True

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
        self.DBService.init_db()

    def add_new_chain(self,chain_name,_proxy):
        self.current_connected_chain.append(chain_name)
        self.current_blockchain_proxy[chain_name] = _proxy
        db = self.DBService.new_db_connect()
        ethereum_latest = 0
        atmchain_latest = 0
        dep = self.DBService.find_rows(db, 'DEPOSIT',"id = (SELECT max(id) FROM DEPOSIT)",['BLOCK_NUMBER_SRC','BLOCK_NUMBER_DEST'])
        if dep != None and dep != tuple():
            ethereum_latest = dep[0][0]
            atmchain_latest = dep[0][1]
        wit = self.DBService.find_rows(db, 'WITHDRAW',"id = (SELECT max(id) FROM WITHDRAW)",['BLOCK_NUMBER_SRC','BLOCK_NUMBER_DEST'])
        if wit != None and wit != tuple():
            if wit[0][1] > ethereum_latest:
                ethereum_latest = wit[0][1] 
            if wit[0][0] > atmchain_latest:
                atmchain_latest = wit[0][0] 
        
        if chain_name == 'ethereum':
            self.polled_blocknumber[chain_name] = ethereum_latest+1
            print('self.polled_blocknumber[ethereum]={}'.format(self.polled_blocknumber[chain_name]))
        if chain_name == 'atmchain':
            self.polled_blocknumber[chain_name] = atmchain_latest+1
            print('self.polled_blocknumber[atmchain]={}'.format(self.polled_blocknumber[chain_name]))

        self.DBService.db_close(db)

    def update_polling_event(self):
        reload(custom_contract_events)
        for key in custom_contract_events.__pollingEventSet__ : 
            chain_name,contract_name,event_name = key.split('_')[:3]
            if chain_name in self.current_connected_chain:
                if self.polling_events.get(chain_name) == None and self.current_blockchain_proxy.get(chain_name) != None:
                    self.polling_events[chain_name] = dict()
                if self.polling_events[chain_name].get(contract_name) == None:
                    self.polling_events[chain_name][contract_name] = dict()
                self.polling_events[chain_name][contract_name][event_name] = custom_contract_events.__pollingEventSet__[key]
            key = chain_name + '_' + contract_name
            if self.polling_events_contract_proxy_cache.get(key) == None and \
                custom_contract_events.__contractInfo__[contract_name]['address']!="" and\
                self.current_blockchain_proxy.get(chain_name) != None:

                self.polling_events_contract_proxy_cache[key] = \
                    self.current_blockchain_proxy[chain_name].attach_contract(
                    contract_name,
                    contract_file=custom_contract_events.__contractInfo__[contract_name]['file'], 
                    contract_address=unhexlify(custom_contract_events.__contractInfo__[contract_name]['address']),)
            

    def run(self):
        db = self.DBService.new_db_connect()
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
                            log.debug('step idle ',contract_name,event_name)
                            continue
                        for event in events:
                            print('\nCATCHED EVENT: {}::{}::{}. block: {}. hash:{}.\n'.format(chain_name,contract_name,event_name,event['block_number'],event['transaction_hash']))
                            if self.DBService.polling_events_callback.get(chain_name + '_' + contract_name + '_' + event_name) == None:
                                log.error('polling_events_callback is nil. ',chain_name,contract_name,event_name)
                                continue
                            DBcallback = self.DBService.polling_events_callback[chain_name + '_' + contract_name + '_' + event_name]
                            sql_sets = self.polling_events[chain_name][contract_name][event_name]['stage']
                            
                            DBcallback(db,sql_sets,event['transaction_hash'],(event))
                        
                self.polled_blocknumber[chain_name] = polling_current_blocknumber+1
        self.DBService.db_close(db)
    
    def stop(self):
        self.is_stopped = True

class PYETHAPI_ATMCHAIN(PYETHAPI):

    def __init__(self,blockchain_service):
        print('init PYETHAPI_ATMCHAIN ...')
        super(PYETHAPI_ATMCHAIN, self).__init__(blockchain_service)
        self.listen_contract_events = LISTEN_CONTRACT_EVENTS_TASK()
        polling = Greenlet.spawn(
            self.listen_contract_events.run,
        ) 
        self.atm_bridge_worker = ATM_BRIDGE_WORKER()
        polling1 = Greenlet.spawn(
            self.atm_bridge_worker.run_deposit_loop,
        ) 
        polling2 = Greenlet.spawn(
            self.atm_bridge_worker.run_withdraw_loop,
        )
    
    def new_blockchain_proxy(self, chain_name,endpoint,keystore_path,admin_account=None):
        print("create blockchain proxy :{} {} {}...".format(chain_name,endpoint,keystore_path))
        _proxy = super(PYETHAPI_ATMCHAIN, self).new_blockchain_proxy(chain_name,endpoint,keystore_path,admin_account)
        print("start listen_contract_events for {} ...".format(chain_name))
        self.listen_contract_events.add_new_chain(chain_name,_proxy)
        print("start atm_bridge_worker for {} ...".format(chain_name))
        self.atm_bridge_worker.add_new_chain(chain_name,_proxy)
        return _proxy

    def deposit_atm_manual(self,id):
        self.atm_bridge_worker.deposit_manual(id)
    def withdraw_atm_manual(self,id):
        self.atm_bridge_worker.withdraw_manual(id)

    def query_atm_bridge_status(self,bridge_type,user,tx_hash):
        if bridge_type == 'deposit':
            return self.atm_bridge_worker.deposit_status(user,tx_hash)
        if bridge_type == 'withdraw':
            return self.atm_bridge_worker.withdraw_status(user,tx_hash)

    """执行离线交易"""
    def send_raw_transaction(self,chain_name,signed_data):
        _proxy = self._get_chain_proxy(chain_name)
        transaction_hash = _proxy.sendRawTransaction(signed_data)
        #过滤向homebridge转atm token的离线交易
        if chain_name == 'ethereum' and transaction_hash !='' and signed_data[76:84] == 'a9059cbb' and signed_data[108:148] == custom_contract_events.__contractInfo__['HomeBridge']['address']:
            sql = custom_contract_events.ATM_Deposit1_insert_DBtable('0x'+transaction_hash)
            self.atm_bridge_worker.DBService.ethereum_ATMToken_Transfer_offline_to_DB(sql)

        if chain_name == 'atmchain':
            print("to be continue .....",signed_data)

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
