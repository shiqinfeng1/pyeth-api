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
log = slogging.getLogger(__name__)

twitter_api = twitter.Api(consumer_key='n3RjtgP7nk1XFAM1ojyJJdo0Z',
                    consumer_secret='XM4Jmy3acY8Mpd6NXqgTAdJMc4TRZe9lzgAvtSw7KD4zozZPDl',
                    access_token_key='895821883433549824-rfN94pGkrJpt31hZO15BVjoSuJOshbE',
                    access_token_secret='tJPLIubFmDkNocLXvYoDnZNDAoKTFr2Bar2smymKk5K90',
                    timeout = 30)
screen_name='ATMChainDev'

class PYETHAPI_ATMCHAIN_REWARDS_PLAN(PYETHAPI_ATMCHAIN):
    def __init__(self,blockchain_service):
        print('init PYETHAPI_ATMCHAIN_REWARDS_PLAN ...')
        super(PYETHAPI_ATMCHAIN_REWARDS_PLAN, self).__init__(blockchain_service)

    def deploy_twitter_rewards_contract(self,sender,chain_name): 
        self._deploy_contract( 
            sender, 
            chain_name,
            'twitter.sol', 'TwitterAccount',
            )

    def bind_account(self,sender,chain_name,contract_name, user_id, user_addr):
        _proxy = self._get_chain_proxy(chain_name)
        contract_proxy = _proxy.get_contract_proxy(
            sender,
            contract_name
        )
        block_number = _proxy.block_number()
        txhash = contract_proxy.bind_account(user_id, user_addr)

        _proxy.poll_contarct_transaction_result(txhash,block_number,contract_proxy,'Log_bind_account',user_id) 

    def unbind_account(self,sender,chain_name,contract_name, user_id):
        _proxy = self._get_chain_proxy(chain_name)
        contract_proxy = _proxy.get_contract_proxy(
            sender,
            contract_name
        )
        block_number = _proxy.block_number()
        txhash = contract_proxy.bind_account(user_id)

        _proxy.poll_contarct_transaction_result(txhash,block_number,contract_proxy,'Log_unbind_account',user_id)

    def ATM_rewards(self,sender,chain_name,contract_name,luckyboys_num):
        _proxy = self._get_chain_proxy(chain_name)
        contract_proxy = _proxy.get_contract_proxy(
            sender,
            contract_name
        )
        block_number = _proxy.block_number()
        txhash = contract_proxy.lotus(luckyboys_num, retweet_id, users_list)

        _proxy.poll_contarct_transaction_result(txhash,block_number,contract_proxy,'Log_lotus',retweet_id)
        _proxy.poll_contarct_transaction_result(txhash,block_number,contract_proxy,'Log_lotus_result',retweet_id)    


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
        print('[history messgae id=%s]: %s\n'%(s.id,s.text))
        print('retweet users: {}'.format(twitter_api.GetRetweeters(s.id)))

    print('\n================= user followers      ================================ ')
    users = twitter_api.GetFollowers(screen_name=screen_name)
    for u in users:
        print('[current followers]: %s'%u.name)

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
            try:
                users = twitter_api.GetFollowers(screen_name=screen_name)
                # print('[current followers]: %s'%u.name) for u in users
            except:
                info=sys.exc_info()
                print info[0],":",info[1]
                pass

    def run_monitor_retweet(self):
        print('satrt monitor retweet...')
        while not self.is_stopped:
            gevent.sleep(self.scan_delay2)
            print('\n[ monitor retweet]working start at {}'.format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())))
            try:
                statuses = twitter_api.GetUserTimeline(screen_name=screen_name)
                """
                for s in statuses:
                    print('[history messgae id=%s]: %s\n'%(s.id,s.text))
                    print('retweet users: {}'.format(twitter_api.GetRetweeters(s.id)))
                """
            except:
                info=sys.exc_info()  
                print info[0],":",info[1]
                pass

if __name__ == '__main__':
    twitter_monitor = TwitterMonitor()
    twitter_monitor.run_task()
    event = Event()
    gevent.signal(signal.SIGQUIT, event.set)
    gevent.signal(signal.SIGTERM, event.set)
    gevent.signal(signal.SIGINT, event.set)
    event.wait()
else:
    twitter_monitor = TwitterMonitor()
    t = threading.Thread(target=twitter_monitor.run_task)
    t.setDaemon(True)
    t.start()

