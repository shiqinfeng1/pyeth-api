

class PYETHAPI(object):
    """ CLI interface. """

    def __init__(self,blockchain_service):
        print('init pyeth-api ...')
        self.blockchain_service = blockchain_service

    @property
    def address(self):
        raise NotImplementedError()


    def get_blockchainlist(self, token_address, partner_address):
        raise NotImplementedError()