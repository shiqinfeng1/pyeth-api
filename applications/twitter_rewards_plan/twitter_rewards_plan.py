# -*- coding: UTF-8 -*-

import twitter
import gevent
from gevent.event import AsyncResult
#from api.python import PYETHAPI_ATMCHAIN
from ethereum import slogging
log = slogging.getLogger(__name__)

twitter_api = twitter.Api(consumer_key='n3RjtgP7nk1XFAM1ojyJJdo0Z',
                    consumer_secret='XM4Jmy3acY8Mpd6NXqgTAdJMc4TRZe9lzgAvtSw7KD4zozZPDl',
                    access_token_key='895821883433549824-rfN94pGkrJpt31hZO15BVjoSuJOshbE',
                    access_token_secret='tJPLIubFmDkNocLXvYoDnZNDAoKTFr2Bar2smymKk5K90')
screen_name='ATMChainDev'
"""
class PYETHAPI_ATMCHAIN_REWARDS_PLAN(PYETHAPI_ATMCHAIN):
    pass
"""

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
        gevent.spawn(self.run)
        self.scan_delay = 5
        self.is_stopped = False

    def run(self):
        while not self.is_stopped:
            gevent.sleep(self.scan_delay)
            statuses = twitter_api.GetUserTimeline(screen_name=screen_name)
            for s in statuses:
                log.info('[history messgae id=%s]: %s\n'%(s.id,s.text))
                log.info('retweet users: {}'.format(twitter_api.GetRetweeters(s.id)))

if __name__ == '__main__':
    #print_basicinfo()
    TwitterMonitor()
