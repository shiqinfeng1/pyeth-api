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


class BlockchainResource(BaseResource):

    def __init__(self, **kwargs):
        super(BlockchainResource, self).__init__(**kwargs)

    def get(self):
        return self.rest_api.get_our_address()

