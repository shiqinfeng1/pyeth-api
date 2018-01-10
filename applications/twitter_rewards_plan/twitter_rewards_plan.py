# -*- coding: UTF-8 -*-
import sys
import twitter
import gevent
import time
import threading

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

    def ATM_airdrop(self):
        print('s')


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
        self.scan_delay1 = 3
        self.scan_delay2 = 5
        self.is_stopped = False
        t = threading.Thread(target=self.run_thread)
        t.setDaemon(True)
        t.start()
        
    def run_thread(self):
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
                statuses = twitter_api.GetUserTimeline(screen_name=screen_name)
                for s in statuses:
                    log.info('[history messgae id=%s]: %s\n'%(s.id,s.text))
                    log.info('retweet users: %s'%(twitter_api.GetRetweeters(s.id)))
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
                for s in statuses:
                    log.info('[history messgae id=%s]: %s\n'%(s.id,s.text))
                    log.info('retweet users: %s'%(twitter_api.GetRetweeters(s.id)))
            except:
                info=sys.exc_info()  
                print info[0],":",info[1]
                pass


twitter_monitor = TwitterMonitor()

