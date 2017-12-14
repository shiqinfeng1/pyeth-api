

class PYETHAPI(object):
    """ CLI interface. """

    def __init__(self):
        print('init pyeth-api ...')

    @property
    def address(self):
        raise NotImplementedError()


    def get_blockchainlist(self, token_address, partner_address):
        raise NotImplementedError()