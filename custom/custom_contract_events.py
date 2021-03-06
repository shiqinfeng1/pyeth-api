# -*- coding: utf-8 -*-
from ethereum.utils import normalize_address
import time
from binascii import hexlify
"""
event返回数据的list元素结构举例:
{
    'transaction_hash': '0xbb2bc28e8b38a1910e32aad27b01e51051e7ca4bcfcf6227bbaa1c80b25c38d6', 
    'block_number': 6266, 
    '_event_type': 'Minted', 
    '_num': 1233000000000000000000L, 
    '_to': '63f1de588c7ce855b66cf24b595a8991f921130d'
} 
"""

def Token_Transfer_filter_condition(_to):
    
    def filter(event):
        if event['_event_type'] != 'Transfer':
            return False
        if normalize_address(event['_to']) ==  normalize_address(_to):
            return True
        return False

    return filter

def ERC223Token_Minted_filter_condition(_to):
    
    def filter(event):
        if event['_event_type'] != 'Minted':
            return False
        if normalize_address(event['_to']) ==  normalize_address(_to):
            return True
        return False

    return filter

def ERC223Token_Transfer_filter_condition(_from,_to):
    
    def filter(event):
        if event['_event_type'] != 'Transfer':
            return False
        if normalize_address(event['_from']) ==  normalize_address(_from) and \
            normalize_address(event['_to']) ==  normalize_address(_to):
            return True
        return False

    return filter

def TokenExchange_LogLockToken_filter_condition(_user):
    
    def filter(event):
        if event['_event_type'] != 'LogLockToken':
            return False
        if normalize_address(event['_user']) ==  normalize_address(_user):
            return True
        return False

    return filter

def TokenExchange_LogSettleToken_filter_condition(_user):
    
    def filter(event):
        if event['_event_type'] != 'LogSettleToken':
            return False
        if normalize_address(event['_user']) ==  normalize_address(_user):
            return True
        return False

    return filter

def TwitterAccount_Log_lotus_filter_condition(_id):
    
    def filter(event):
        if event['_event_type'] != 'Log_lotus':
            return False
        if event['_id'][:len(_id)] == _id:
            return True
        return False

    return filter

def TwitterAccount_Log_lotus_result_filter_condition(_id):
    
    def filter(event):
        if event['_event_type'] != 'Log_lotus_result':
            return False
        if event['_id'][:len(_id)] == _id:
            return True
        return False

    return filter

def TwitterAccount_Log_unbind_account_filter_condition(_id):
    
    def filter(event):
        if event['_event_type'] != 'Log_unbind_account':
            return False
        if event['_id'][:len(_id)] == _id:
            return True
        return False

    return filter

def TwitterAccount_Log_bind_account_filter_condition(_id):
    
    def filter(event):
        if event['_event_type'] != 'Log_bind_account':
            return False
        if event['_id'][:len(_id)] == _id:
            return True
        return False

    return filter

def ForeignBridge_Deposit_filter_condition():
    def filter(event):
        if event['_event_type'] != 'Deposit':
            return False
        return True
    return filter

def ForeignBridge_TransferBack_filter_condition():
    def filter(event):
        if event['_event_type'] != 'TransferBack':
            return False
        return True
    return filter

def HomeBridge_Withdraw_filter_condition():
    def filter(event):
        if event['_event_type'] != 'Withdraw':
            return False
        return True
    return filter

__conditionSet__ = {
    'ATMToken_Transfer': Token_Transfer_filter_condition,
    'Token_Transfer': Token_Transfer_filter_condition,

    'ERC223Token_Minted': ERC223Token_Minted_filter_condition,
    'ERC223Token_Transfer': ERC223Token_Transfer_filter_condition,

    'TokenExchange_LogLockToken':TokenExchange_LogLockToken_filter_condition,
    'TokenExchange_LogSettleToken':TokenExchange_LogSettleToken_filter_condition,

    'TwitterAccount_Log_bind_account': TwitterAccount_Log_bind_account_filter_condition,
    'TwitterAccount_Log_unbind_account': TwitterAccount_Log_unbind_account_filter_condition,
    'TwitterAccount_Log_lotus_result': TwitterAccount_Log_lotus_result_filter_condition,
    'TwitterAccount_Log_lotus': TwitterAccount_Log_lotus_filter_condition,

    'ForeignBridge_Deposit': ForeignBridge_Deposit_filter_condition,
    'ForeignBridge_TransferBack': ForeignBridge_TransferBack_filter_condition,
    'HomeBridge_Withdraw': HomeBridge_Withdraw_filter_condition,
}


def ATM_Deposit1_insert_DBtable(tx_hash):
    sql = "INSERT INTO DEPOSIT(USER_ADDRESS, AMOUNT, STAGE, \
        CHAIN_NAME_SRC, TRANSACTION_HASH_SRC, BLOCK_NUMBER_SRC, \
        CHAIN_NAME_DEST, TRANSACTION_HASH_DEST, BLOCK_NUMBER_DEST,TIME_STAMP) \
        VALUES ('%s', '%d', '%d', '%s', '%s', '%d', '%s', '%s', '%d', '%s')" % \
        ('unknow', 0, 1, 'ethereum', tx_hash, 0, 'unknow', 'unknow', 0,time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())))
    return sql

def ATM_Withdraw1_insert_DBtable(tx_hash):
    sql = "INSERT INTO WITHDRAW(USER_ADDRESS, AMOUNT, STAGE, \
        CHAIN_NAME_SRC, TRANSACTION_HASH_SRC, BLOCK_NUMBER_SRC, \
        CHAIN_NAME_DEST, TRANSACTION_HASH_DEST, BLOCK_NUMBER_DEST,TIME_STAMP) \
        VALUES ('%s', '%d', '%d', '%s', '%s', '%d', '%s', '%s', '%d', '%s')" % \
        ('unknow', 0, 1, 'atmchain', tx_hash, 0, 'unknow', 'unknow', 0,time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())))
    return sql

def ATM_Deposit2_update_DBtable(event):
    sql = "UPDATE DEPOSIT SET USER_ADDRESS = '%s', STAGE = '%d', BLOCK_NUMBER_SRC = '%d', AMOUNT = '%d', TIME_STAMP = '%s' \
        WHERE TRANSACTION_HASH_SRC = '%s'" % \
        (event['_from'], 2, event['block_number'],event['_value'],time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())), event['transaction_hash'])
    return sql

def ATM_Withdraw2_update_DBtable(event):
    print('step a')
    sql = "UPDATE WITHDRAW SET USER_ADDRESS = '%s', STAGE = '%d', BLOCK_NUMBER_SRC = '%d', AMOUNT = '%d', TIME_STAMP = '%s' \
        WHERE TRANSACTION_HASH_SRC = '%s'" % \
        (event['_from'], 2, event['block_number'],event['_value'],time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())), event['transaction_hash'])
    print('step b')
    return sql

def ATM_Deposit2_insert_DBtable(event):
    sql = "INSERT INTO DEPOSIT(USER_ADDRESS, AMOUNT, STAGE, \
        CHAIN_NAME_SRC, TRANSACTION_HASH_SRC, BLOCK_NUMBER_SRC, \
        CHAIN_NAME_DEST, TRANSACTION_HASH_DEST, BLOCK_NUMBER_DEST,TIME_STAMP) \
        VALUES ('%s', '%d', '%d', '%s', '%s', '%d', '%s', '%s', '%d', '%s')" % \
        (event['_from'], event['_value'], 2, 'ethereum', event['transaction_hash'], event['block_number'], '', '', 0,time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())))
    return sql

def ATM_Withdraw2_insert_DBtable(event):
    sql = "INSERT INTO WITHDRAW(USER_ADDRESS, AMOUNT, STAGE, \
        CHAIN_NAME_SRC, TRANSACTION_HASH_SRC, BLOCK_NUMBER_SRC, \
        CHAIN_NAME_DEST, TRANSACTION_HASH_DEST, BLOCK_NUMBER_DEST,TIME_STAMP) \
        VALUES ('%s', '%d', '%d', '%s', '%s', '%d', '%s', '%s', '%d', '%s')" % \
        (event['recipient'], event['value'], 2, 'atmchain', event['transaction_hash'], event['block_number'], '', '', 0,time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())))
    return sql

def ATM_Deposit3_update_DBtable(event):
    sql = "UPDATE DEPOSIT SET STAGE = '%d', \
        CHAIN_NAME_DEST = '%s', TRANSACTION_HASH_DEST = '%s', BLOCK_NUMBER_DEST = '%d',TIME_STAMP = '%s' \
        WHERE TRANSACTION_HASH_SRC = '%s'" % \
        (3, 'atmchain', event['transaction_hash'], event['block_number'],time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())), '0x'+hexlify(event['transactionHash']))
    return sql
# TRANSACTION_HASH_SRC 是withdraw操作的源链，即atmchain
def ATM_Withdraw3_update_DBtable(event):
    sql = "UPDATE WITHDRAW SET STAGE = '%d', \
        CHAIN_NAME_DEST = '%s', TRANSACTION_HASH_DEST = '%s', BLOCK_NUMBER_DEST = '%d',TIME_STAMP = '%s' \
        WHERE TRANSACTION_HASH_SRC = '%s'" % \
        (3, 'ethereum', event['transaction_hash'], event['block_number'],time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())), '0x'+hexlify(event['transactionHash']))
    return sql
""" rinkeby
__contractInfo__ = {
    'ContractAddress':{'file':'ContractAddress.sol','address':"7d88a18649fe5de4f35c701dad88d97b0d762ec2"},
    'ATMToken':{'file':'ATMToken.sol','address':"42cca44fa7e65ba9051f98469df70bccf50b1cf4"},
    'HomeBridge':{'file':'bridge_v2.sol','address':"a3b5583703b9316246917d3ee9dcd7aed8eb9cff"},
    'ForeignBridge':{'file':'bridge_v2.sol','address':"6db0d943ba112497281a7eabee52a06c0d49f9da"},
}
"""
__contractInfo__ = {
    'ContractAddress':{'file':'ContractAddress.sol','address':"272ffa2cf090815e5cac7b89ad5e3266800f0ff4"},
    'ATMToken':{'file':'ATMToken.sol','address':"9B11EFcAAA1890f6eE52C6bB7CF8153aC5d74139"},
    'HomeBridge':{'file':'bridge_v2.sol','address':"7d88a18649fe5de4f35c701dad88d97b0d762ec2"},
    'ForeignBridge':{'file':'bridge_v2.sol','address':"1d151c966b875188583e35500b3473eb84e75d71"},
}

__pollingEventSet__ = {
    'ethereum_ATMToken_Transfer': {'filter_args':[__contractInfo__['HomeBridge']['address']],'stage':[ATM_Deposit2_update_DBtable,ATM_Deposit2_insert_DBtable]},
    'atmchain_ForeignBridge_Deposit':{'filter_args':[],'stage':[ATM_Deposit3_update_DBtable]},
    'atmchain_ForeignBridge_TransferBack': {'filter_args':[],'stage':[ATM_Withdraw2_update_DBtable,ATM_Withdraw2_insert_DBtable]},
    'ethereum_HomeBridge_Withdraw':{'filter_args':[],'stage':[ATM_Withdraw3_update_DBtable]},
}


__DBConfig__ = {
    'host':"localhost",
    'port':3306,
    'user':"root",
    'password':"atmchain666",
    'db':"atm_bridge",
    'charset':"utf8",
    'autocommit':True,
}
__BridgeConfig__ = {
    'limit':10000*(10**8)
}

__chainConfig__ = {
    'ethereum':{'endpoint':"mainnet"},
    'atmchain':{'endpoint':"localhost:21024"}
}
    

