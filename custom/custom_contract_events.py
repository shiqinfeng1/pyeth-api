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

def ForeignBridge_Withdraw_filter_condition():
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
    'ForeignBridge_Withdraw': ForeignBridge_Withdraw_filter_condition,
}


def ATM_Deposit1_insert_DBtable(tx_hash):
    sql = "INSERT INTO DEPOSIT(USER_ADDRESS, AMOUNT, STAGE, \
        CHAIN_NAME_SRC, TRANSACTION_HASH_SRC, BLOCK_NUMBER_SRC, \
        CHAIN_NAME_DEST, TRANSACTION_HASH_DEST, BLOCK_NUMBER_DEST,TIME_STAMP) \
        VALUES ('%s', '%d', '%d', '%s', '%s', '%d', '%s', '%s', '%d', '%s')" % \
        ('', 0, 1, 'ethereum', tx_hash, 0, '', '', 0,time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())))

    return sql

def ATM_Deposit2_update_DBtable(event):
    sql = "UPDATE DEPOSIT SET STAGE = '%d', BLOCK_NUMBER_SRC = '%d', TIME_STAMP = '%s') \
        WHERE TRANSACTION_HASH_SRC = '%s'" % \
        (2, event['block_number'],time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())), event['transaction_hash'])

    return sql

def ATM_Deposit2_insert_DBtable(event):
    sql = "INSERT INTO DEPOSIT(USER_ADDRESS, AMOUNT, STAGE, \
        CHAIN_NAME_SRC, TRANSACTION_HASH_SRC, BLOCK_NUMBER_SRC, \
        CHAIN_NAME_DEST, TRANSACTION_HASH_DEST, BLOCK_NUMBER_DEST,TIME_STAMP) \
        VALUES ('%s', '%d', '%d', '%s', '%s', '%d', '%s', '%s', '%d', '%s')" % \
        (event['_from'], event['_value'], 3, 'ethereum', event['transaction_hash'], event['block_number'], '', '', 0,time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())))

    return sql

def ATM_Deposit3_update_DBtable(event):
    sql = "UPDATE DEPOSIT SET STAGE = '%d', \
        CHAIN_NAME_DEST = '%s', TRANSACTION_HASH_DEST = '%s', BLOCK_NUMBER_DEST = '%d',TIME_STAMP = '%s' \
        WHERE TRANSACTION_HASH_SRC = '%s'" % \
        (4, 'atmchain', event['transaction_hash'], event['block_number'],time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())), '0x'+hexlify(event['transactionHash']))

    return sql

__pollingEventSet__ = {
    'ethereum_ATMToken_Transfer': {'filter_args':["c1aaac2d2739169d3d5dfe32e97be0678a7abf39"],'stage':[ATM_Deposit2_update_DBtable,ATM_Deposit2_insert_DBtable]},
    'atmchain_ForeignBridge_Deposit':{'filter_args':[],'stage':[ATM_Deposit3_update_DBtable]},
}

__contractInfo__ = {
    'ContractAddress':{'file':'ContractAddress.sol','address':"5f045e04d122a6d6c194fcdfbd6a2bcb24c1c343"},#de66acec6aa735d8407f57a5e5746e92777d9050
    'ATMToken':{'file':'ATMToken.sol','address':"37a016410d9430696195eb07e8614d21873c8db1"},#1343f98dcb7c867d553696d506cc87da995b75d2
    'HomeBridge':{'file':'bridge.sol','address':"c1aaac2d2739169d3d5dfe32e97be0678a7abf39"},#69eb6e2b2dc66268482467b9b35369dc5c656cf0
    'ForeignBridge':{'file':'bridge.sol','address':"4947774318f05231bb896a69d175655017a783c3"},#45d744d325160791941a7689f70ed841cf49207f
}

__DBConfig__ = {
    'host':"localhost",
    'port':3306,
    'user':"root",
    'password':"12345678",
    'db':"atm_bridge",
    'charset':"utf8",
}
__BridgeConfig__ = {
    'limit':10000*(10**8)
}
    

