# -*- coding: utf-8 -*-

from webargs.flaskparser import use_kwargs
from flask_restful import Resource
from flask import Blueprint


def create_blueprint():
    # Take a look at this SO question on hints how to organize versioned
    # API with flask:
    # http://stackoverflow.com/questions/28795561/support-multiple-api-versions-in-flask#28797512
    return Blueprint('v1_resources', __name__)


class BaseResource(Resource):
    def __init__(self, **kwargs):
        super(BaseResource, self).__init__()
        self.rest_api = kwargs['rest_api_object']


class AddressResource(BaseResource):

    def __init__(self, **kwargs):
        super(AddressResource, self).__init__(**kwargs)

    def get(self):
        return self.rest_api.get_admin_address()

"""
class TransferToTargetResource(BaseResource):
    
    post_schema = TransferSchema(
        exclude=('initiator_address', 'target_address', 'token_address')
    )

    def __init__(self, **kwargs):
        super(TransferToTargetResource, self).__init__(**kwargs)

    @use_kwargs(post_schema, locations=('json',))
    def post(self, token_address, target_address, amount, identifier):
        return self.rest_api.initiate_transfer(
            token_address=token_address,
            target_address=target_address,
            amount=amount,
            identifier=identifier,
        )
"""