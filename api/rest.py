from flask import Flask, make_response, url_for
from flask.json import jsonify
from flask_restful import Api, abort
from flask_cors import CORS
from webargs.flaskparser import parser
from binascii import hexlify
from api.v1.resources import (
    create_blueprint,
    BridgeStatusResource,
    TokensResource,
    RawTransactionResource,
    NonceResource,
    DepositLimitResource,
    BalanceResource,
)

class APIServer(object):

    def __init__(self, rest_api, cors_domain_list=None):
        self.rest_api = rest_api
        self.blueprint = create_blueprint()
        if self.rest_api.version == 1:
            self.flask_api_context = Api(
                self.blueprint,
                prefix="/api/v1",
            )
        else:
            raise ValueError('Invalid api version: {}'.format(self.rest_api.version))

        self.flask_app = Flask(__name__)
        self.flask_app.debug = True
        if cors_domain_list:
            CORS(self.flask_app, origins=cors_domain_list)
        self._add_default_resources()
        self.flask_app.register_blueprint(self.blueprint)

    def _add_default_resources(self):
        self.add_resource(TokensResource, '/asset')
        self.add_resource(BridgeStatusResource, '/QueryBridgeStatus')
        self.add_resource(RawTransactionResource, '/SendRawTransaction')
        self.add_resource(NonceResource, '/QueryNonce')
        self.add_resource(DepositLimitResource, '/QueryDepositLimit')
        self.add_resource(BalanceResource, '/QueryBalance')

    def add_resource(self, resource_cls, route):
        self.flask_api_context.add_resource(
            resource_cls,
            route,
            resource_class_kwargs={'rest_api_object': self.rest_api}
        )

    def run(self, port, **kwargs):
        if 'host' in kwargs:
            raise ValueError('The server host is hardcoded, can\'t set it')
        self.flask_app.run(port=port, host='0.0.0.0', **kwargs)


class RestAPI(object):
    """
    This wraps around the actual API in api/python.
    It will provide the additional, neccessary RESTful logic and
    the proper JSON-encoding of the Objects provided by the API
    """
    version = 1

    def __init__(self, pyeth_api):
        self.pyeth_api = pyeth_api

    def deploy_contract(self, chain, user_address, decimals, total_suply, name, symbol):
        _proxy = self.pyeth_api._get_chain_proxy(chain)
        userToken = _proxy.deploy_contract( 
            _proxy.account_manager.admin_account, 
            'userToken.sol', 'userToken',
            (hexlify(user_address),total_suply,hexlify(symbol),decimals,hexlify(name)),
            password = _proxy.account_manager.get_admin_password(),
        )
        if userToken == None:
            return {'result':'fail','contract_address': ''}
        address = userToken.address
        print("deployed address:", hexlify(address))
        return {'result':'success','contract_address': hexlify(address)}

    def query_atm_bridge_status(self, bridge_type,user_address, transaction_hash):
        result = self.pyeth_api.query_atm_bridge_status(bridge_type,user_address, transaction_hash)
        if result == None or result == list():
            return {'result':'fail','bridge_type':bridge_type,'atm_bridge_status': list()}
        
        keys = ['ID','USER_ADDRESS','AMOUNT','STAGE','CHAIN_NAME_SRC','TRANSACTION_HASH_SRC','BLOCK_NUMBER_SRC','CHAIN_NAME_DEST','TRANSACTION_HASH_DEST','BLOCK_NUMBER_DEST','TIME_STAMP']
        total = list()
        for rec in result:
            dictionary = dict(zip(keys, list(rec)))
            total.append(dictionary)

        return {'result':'success','bridge_type':bridge_type,'atm_bridge_status': total}
    
    def send_raw_transaction(self, chain_name,signed_data):
        result = self.pyeth_api.send_raw_transaction(chain_name,signed_data)
        if result == '':
            return {'result':'fail','transaction_hash': result}
        return {'result':'success','transaction_hash': '0x'+result}

    def query_nonce(self, chain_name,user):
        result = self.pyeth_api.get_nonce(chain_name,user)
        return {'result':'success','nonce': result}

    def query_deposit_limit(self):
        result = self.pyeth_api.get_deposit_limit()
        return {'result':'success','deposit_limit': result}
    
    def query_balance(self,user):
        result = self.pyeth_api.query_atmchain_balance('ethereum','atmchain',user)
        if result == dict():
            return {'result':'fail','balance': dict()}
        return {'result':'success','balance': result}