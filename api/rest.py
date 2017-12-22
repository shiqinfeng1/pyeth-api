from flask import Flask, make_response, url_for
from flask.json import jsonify
from flask_restful import Api, abort
from flask_cors import CORS
from webargs.flaskparser import parser
from pyethapp.jsonrpc import address_encoder

from api.v1.encoding import (
    HexAddressConverter,
)
from api.v1.resources import (
    create_blueprint,
    AddressResource,
)

class APIServer(object):

    # flask TypeConverter
    # links argument-placeholder in route (e.g. '/<hexaddress: channel_address>') to the Converter
    _type_converter_mapping = {
        'hexaddress': HexAddressConverter
    }

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
        self._register_type_converters()
        self.flask_app.register_blueprint(self.blueprint)

    def _add_default_resources(self):
        self.add_resource(AddressResource, '/adminAddress')
        """
        self.add_resource(ChannelsResource, '/channels')
        self.add_resource(
            ChannelsResourceByChannelAddress,
            '/channels/<hexaddress:channel_address>'
        )
        self.add_resource(TokensResource, '/tokens')
        self.add_resource(
            PartnersResourceByTokenAddress,
            '/tokens/<hexaddress:token_address>/partners'
        )
        self.add_resource(NetworkEventsResource, '/events/network')
        """

    def _register_type_converters(self, additional_mapping=None):
        # an additional mapping concats to class-mapping and will overwrite existing keys
        if additional_mapping:
            mapping = dict(self._type_converter_mapping, **additional_mapping)
        else:
            mapping = self._type_converter_mapping

        for key, value in mapping.items():
            self.flask_app.url_map.converters[key] = value

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

    def get_admin_address(self):
        return {'admin_address': self.pyeth_api.adminAddress}
