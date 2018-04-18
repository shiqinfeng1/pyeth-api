# -*- coding: utf-8 -*-

from webargs.flaskparser import use_kwargs
from flask_restful import Resource
from flask import Blueprint
from api.v1.encoding import (
    TokenSchema,
    DepositStatusSchema,
    RawTransactionSchema,
    NonceSchema,
    BalanceSchema,
    DepositLimitSchema,
)

def create_blueprint():
    # Take a look at this SO question on hints how to organize versioned
    # API with flask:
    # http://stackoverflow.com/questions/28795561/support-multiple-api-versions-in-flask#28797512
    return Blueprint('v1_resources', __name__)


class BaseResource(Resource):
    def __init__(self, **kwargs):
        super(BaseResource, self).__init__()
        self.rest_api = kwargs['rest_api_object']

class TokensResource(BaseResource):
    
    post_schema = TokenSchema()

    def __init__(self, **kwargs):
        super(TokensResource, self).__init__(**kwargs)

    @use_kwargs(post_schema, locations=('json',))
    def post(self, chain_name,user_address,decimals,total_suply,name,symbol):
        return self.rest_api.deploy_contract(
            chain = chain_name,
            user_address=user_address,
            decimals=decimals,
            total_suply=total_suply,
            name=name,
            symbol=symbol,
        )

class DepositStatusResource(BaseResource):
    
    post_schema = DepositStatusSchema()

    def __init__(self, **kwargs):
        super(DepositStatusResource, self).__init__(**kwargs)

    @use_kwargs(post_schema, locations=('json',))
    def post(self, user_address,transaction_hash):
        return self.rest_api.query_atm_deposit_status(
            user_address,transaction_hash
        )

class RawTransactionResource(BaseResource):
    
    post_schema = RawTransactionSchema()

    def __init__(self, **kwargs):
        super(RawTransactionResource, self).__init__(**kwargs)

    @use_kwargs(post_schema, locations=('json',))
    def post(self, chain_name,signed_data):
        return self.rest_api.send_raw_transaction(
            chain_name,signed_data
        )

class NonceResource(BaseResource):
    
    post_schema = NonceSchema()

    def __init__(self, **kwargs):
        super(NonceResource, self).__init__(**kwargs)

    @use_kwargs(post_schema, locations=('json',))
    def post(self, chain_name,user):
        return self.rest_api.query_nonce(
            chain_name,user
        )

class DepositLimitResource(BaseResource):
    
    post_schema = DepositLimitSchema()

    def __init__(self, **kwargs):
        super(DepositLimitResource, self).__init__(**kwargs)

    @use_kwargs(post_schema, locations=('json',))
    def post(self):
        return self.rest_api.query_deposit_limit()

class BalanceResource(BaseResource):
    
    post_schema = BalanceSchema()

    def __init__(self, **kwargs):
        super(BalanceResource, self).__init__(**kwargs)

    @use_kwargs(post_schema, locations=('json',))
    def post(self,user):
        return self.rest_api.query_balance(user)