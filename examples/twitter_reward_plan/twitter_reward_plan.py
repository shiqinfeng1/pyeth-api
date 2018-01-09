from ethereum import slogging
import twitter
api = twitter.Api(consumer_key='n3RjtgP7nk1XFAM1ojyJJdo0Z',
                    consumer_secret='XM4Jmy3acY8Mpd6NXqgTAdJMc4TRZe9lzgAvtSw7KD4zozZPDl',
                    access_token_key='895821883433549824-rfN94pGkrJpt31hZO15BVjoSuJOshbE',
                    access_token_secret='tJPLIubFmDkNocLXvYoDnZNDAoKTFr2Bar2smymKk5K90')

class TwitterMonitor(object):
    
    request_timeout = 8.

    def __init__(self):
        self.deferred = None
        gevent.spawn(self.run)

    def run(self):
        self.deferred = AsyncResult()
        self.proto.send_getblockheaders(self.config['DAO_FORK_BLKNUM'], 1, 0)
        try:
            dao_headers = self.deferred.get(block=True, timeout=self.request_timeout)
            log.debug("received DAO challenge answer", proto=self.proto, answer=dao_headers)
            result = len(dao_headers) == 1 and \
                    dao_headers[0].hash == self.config['DAO_FORK_BLKHASH'] and \
                    dao_headers[0].extra_data == self.config['DAO_FORK_BLKEXTRA']
            self.chainservice.on_dao_challenge_answer(self.proto, result)
        except gevent.Timeout:
            log.debug('challenge dao timed out', proto=self.proto)
            self.chainservice.on_dao_challenge_answer(self.proto, False)

    def receive_blockheaders(self, proto, blockheaders):
        log.debug('blockheaders received', proto=proto, num=len(blockheaders))
        if proto != self.proto:
            return
        self.deferred.set(blockheaders)

if __name__ == '__main__':
    slogging.configure(':DEBUG')
    print('================= twitter api info  ================================ ')
    print(api.VerifyCredentials())
    print('================= user status       ================================ ')
    statuses = api.GetUserTimeline(screen_name='rex shi')
    print([s.text for s in statuses])
    print('================= user followers      ================================ ')
    users = api.GetFollowers()
    print([u.name for u in users])
    print('================= test end          ================================ ')
    #twitter_monitor = TwitterMonitor()
