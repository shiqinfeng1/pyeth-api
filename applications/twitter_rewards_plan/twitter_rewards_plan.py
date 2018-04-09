# -*- coding: UTF-8 -*-
import sys
import twitter
import gevent
from gevent.event import Event
import signal
import time
import threading
sys.path.append('../../')
from api.python import PYETHAPI_ATMCHAIN
from ethereum import slogging
from binascii import hexlify, unhexlify

log = slogging.getLogger(__name__)

"""
twitter_api = twitter.Api(consumer_key='n3RjtgP7nk1XFAM1ojyJJdo0Z',
                    consumer_secret='XM4Jmy3acY8Mpd6NXqgTAdJMc4TRZe9lzgAvtSw7KD4zozZPDl',
                    access_token_key='895821883433549824-rfN94pGkrJpt31hZO15BVjoSuJOshbE',
                    access_token_secret='tJPLIubFmDkNocLXvYoDnZNDAoKTFr2Bar2smymKk5K90',
                    timeout = 30)
"""
screen_name='ATMChainDev'
all_followers_by_id= dict()
all_followers_by_name= dict()


class PYETHAPI_ATMCHAIN_REWARDS_PLAN(PYETHAPI_ATMCHAIN):
    def __init__(self,blockchain_service):
        print('init PYETHAPI_ATMCHAIN_REWARDS_PLAN ...')
        super(PYETHAPI_ATMCHAIN_REWARDS_PLAN, self).__init__(blockchain_service)

    def deploy_twitter_rewards_contract(self,sender,chain_name): 
        _proxy = self._get_chain_proxy(chain_name)
        contract_proxy = _proxy.deploy_contract( 
            sender,
            'twitter.sol', 'TwitterAccount',
            tuple()
            )

    def bind_account(self,sender,chain_name, user_id, user_addr,contract_address=None):
        _proxy = self._get_chain_proxy(chain_name)
        if contract_address[:2]=='0x':
            contract_address = contract_address[2:]
        contract_proxy = _proxy.attach_contract(
            'TwitterAccount',
            contract_file='twitter.sol', 
            contract_address=unhexlify(contract_address),
            attacher=sender, 
        )
        block_number = _proxy.block_number()
        txhash = contract_proxy.bind_account(user_id, user_addr)

        _proxy.poll_contarct_transaction_result(txhash,block_number,contract_proxy,'Log_bind_account',user_id) 

    def unbind_account(self,sender,chain_name, user_id,contract_address=None):
        _proxy = self._get_chain_proxy(chain_name)
        if contract_address[:2]=='0x':
            contract_address = contract_address[:2]
        contract_proxy = _proxy.attach_contract(
            'TwitterAccount',
            contract_file='twitter.sol', 
            contract_address=unhexlify(contract_address),
            attacher=sender, 
        )
        block_number = _proxy.block_number()
        txhash = contract_proxy.bind_account(user_id)

        _proxy.poll_contarct_transaction_result(txhash,block_number,contract_proxy,'Log_unbind_account',user_id)

    def query_bindinfo(self, sender, chain_name, screen_name, contract_address=None):
        _proxy = self._get_chain_proxy(chain_name)
        if contract_address[:2]=='0x':
            contract_address = contract_address[:2]
        contract_proxy = _proxy.attach_contract(
            'TwitterAccount',
            contract_address=unhexlify(contract_address),
            contract_file='twitter.sol', 
            attacher=sender, 
        )
        if screen_name not in all_followers_by_name.keys():
            printf('screen_name: {} is not our followers.'.format(screen_name))
            return 
        block_number = _proxy.block_number()
        txhash = contract_proxy.query_bindinfo(str(all_followers_by_name[screen_name]))

        _proxy.poll_contarct_transaction_result(txhash,block_number,contract_proxy,'Log_bind_account',str(all_followers_by_name[screen_name]))

    def twitter_status_list(self):
        statuses = get_status_list('ATMChainDev')
        for s in statuses:
            print('[ history status id= %s ]: %s...\n'%(s.id,s.text[:40]))
    
    def retwitter_list(self,status_id):
        retweeters = get_retweeters(status_id)
        if retweeters == None:
            print('get_retweeters fail.')
            return 
        for s in retweeters:
            if s not in all_followers_by_id.keys():
                print('retweeters id = {:20} not followers '.format(s))
            else:
                print('retweeters id = {:20} screen_name = {}'.format(s,all_followers_by_id[s]))

    def get_luckyboys(self,sender,chain_name,status_id,luckyboys_num,contract_address=None):
        users_list=list()
        if isinstance(status_id, (int, long)):
            status_id = str(status_id)
            
        followers = get_followers('ATMChainDev')
        retweeters = get_retweeters(status_id)
        for retweeter in retweeters:
            if retweeter in followers:
                users_list.append(str(retweeter))

        print('status_id: {} validate users list= {}'.format(status_id,users_list))

        _proxy = self._get_chain_proxy(chain_name)
        if contract_address[:2]=='0x':
            contract_address = contract_address[:2]
        contract_proxy = _proxy.attach_contract(
            'TwitterAccount',
            contract_address=unhexlify(contract_address),
            contract_file='twitter.sol', 
            attacher=sender, 
        )
        block_number = _proxy.block_number()
        txhash = contract_proxy.lotus(luckyboys_num, status_id, users_list)

        _proxy.poll_contarct_transaction_result(txhash,block_number,contract_proxy,'Log_lotus',status_id)
        event_key, event = _proxy.poll_contarct_transaction_result(txhash,block_number,contract_proxy,'Log_lotus_result',status_id)    
        r1 = event[0]['luckyboys']
        r2 = event[0]['luckyboys_addr']
        print('\n================= luckyboys list  =================== ')
        
        for (i1, i2) in zip(r1,r2):
            sid = i1[:i1.find('\x00')]
            print('luckyboys: {:20}({:20}) address = {} '.format(all_followers_by_id[sid],sid,i2))

def print_basicinfo():
    print('================= start running twitter monitor  =================== ')

    print('================= twitter api info  ================================ ')
    data=twitter_api.VerifyCredentials().AsDict()
    for keys,values in data.items():
        if keys == 'status':
            print('{:32}:'.format(keys))
            for k,v in values.items():
                print('    {:24}: {}'.format(k,v))
        else:
            print('{:32}: {}'.format(keys,values))
    
    print('\n================= user {} status       ================================ '.format(screen_name))
    statuses = twitter_api.GetUserTimeline(screen_name=screen_name)
    for s in statuses:
        print('[ history status id= %s ]: %s\n'%(s.id,s.text))
        print('retweet users: {}'.format(twitter_api.GetRetweeters(s.id)))

    print('\n================= user followers      ================================ ')
    users = twitter_api.GetFollowers(screen_name=screen_name)
    for u in users:
        print('[current followers]: %s'%u.name)

def get_followers(screenname):
    users=None
    try:
        users = twitter_api.GetFollowers(screen_name=screenname)
        all_followers_by_id.clear()
        all_followers_by_name.clear()
        for u in users:
            all_followers_by_name[u.name] = u.id
            all_followers_by_id[u.id] = u.name
            print('[current followers] id = %-20s name = %s'%(u.id,u.name))
    except:
        info=sys.exc_info()
        print info[0],":",info[1]
        pass
    
    if users != None:
        return [u.id for u in users]
    else: 
        return None

def get_status_list(screenname):
    statuses=None
    try:
        statuses = twitter_api.GetUserTimeline(screen_name=screenname)
    except:
        info=sys.exc_info()
        print info[0],":",info[1]
        pass
    return  statuses

def get_retweeters(status_id):
    retweeters=None
    try:
        retweeters = twitter_api.GetRetweeters(status_id)
    except:
        info=sys.exc_info()  
        print info[0],":",info[1]
        pass
    return retweeters

class TwitterMonitor(object):
    
    def __init__(self):
        #print_basicinfo()
        self.scan_delay1 = 67
        self.scan_delay2 = 37
        self.is_stopped = False
        
    def run_task(self):
        gevent.joinall([
            gevent.spawn(self.run_monitor_retweet),
            gevent.spawn(self.run_monitor_followers)
        ])

    def run_monitor_followers(self):
        print('satrt monitor followers...')
        while not self.is_stopped:
            gevent.sleep(self.scan_delay1)
            print('\n[ monitor followers]working start at {}'.format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())))
            get_followers('ATMChainDev')

    def run_monitor_retweet(self):
        print('satrt monitor retweet...')
        while not self.is_stopped:
            gevent.sleep(self.scan_delay2)
            print('\n[ monitor retweet]working start at {}'.format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())))
            
            statuses = get_status_list('ATMChainDev')
            for s in statuses:
                print('[history status id= %s ]: %s\n'%(s.id,s.text))
                get_retweeters(s.id)


if __name__ == '__main__':
    twitter_monitor = TwitterMonitor()
    twitter_monitor.run_task()
    event = Event()
    gevent.signal(signal.SIGQUIT, event.set)
    gevent.signal(signal.SIGTERM, event.set)
    gevent.signal(signal.SIGINT, event.set)
    event.wait()
""" do not start a thread because of twitter warning: 'Rate limit exceeded'
else:
    twitter_monitor = TwitterMonitor()
    t = threading.Thread(target=twitter_monitor.run_task)
    t.setDaemon(True)
    t.start()
"""
origin_followers = get_followers('ATMChainDev')
