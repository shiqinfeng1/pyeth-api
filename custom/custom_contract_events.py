# -*- coding: utf-8 -*-
from ethereum.utils import normalize_address

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

__conditionSet__ = {
    'ERC223Token_Minted': ERC223Token_Minted_filter_condition,
    'ERC223Token_Transfer': ERC223Token_Transfer_filter_condition,
    'TokenExchange_LogLockToken':TokenExchange_LogLockToken_filter_condition,
    'TokenExchange_LogSettleToken':TokenExchange_LogSettleToken_filter_condition,
    'TwitterAccount_Log_bind_account': TwitterAccount_Log_bind_account_filter_condition,
    'TwitterAccount_Log_unbind_account': TwitterAccount_Log_unbind_account_filter_condition,
    'TwitterAccount_Log_lotus_result': TwitterAccount_Log_lotus_result_filter_condition,
    'TwitterAccount_Log_lotus': TwitterAccount_Log_lotus_filter_condition,
}


    

