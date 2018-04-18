# -*- coding: utf-8 -*-

from marshmallow import (
    fields,
    post_dump,
    post_load,
    pre_load,
    Schema,
    SchemaOpts,
)
from service.utils import (
    address_encoder,
    address_decoder,
)
from werkzeug.routing import (
    BaseConverter,
    ValidationError,
)
class BaseOpts(SchemaOpts):
    """
    This allows for having the Object the Schema encodes to inside of the class Meta
    """
    def __init__(self, meta):
        SchemaOpts.__init__(self, meta)
        self.decoding_class = getattr(meta, 'decoding_class', None)
        
class AddressField(fields.Field):
    default_error_messages = {
        'missing_prefix': 'Not a valid hex encoded address, must be 0x prefixed.',
        'invalid_data': 'Not a valid hex encoded address, contains invalid characters.',
        'invalid_size': 'Not a valid hex encoded address, decoded address is not 20 bytes long.',
    }

    def _serialize(self, value, attr, obj):
        return address_encoder(value)

    def _deserialize(self, value, attr, data):
        if value[:2] != '0x':
            self.fail('missing_prefix')

        try:
            value = value[2:].decode('hex')
        except TypeError:
            self.fail('invalid_data')

        if len(value) != 20:
            self.fail('invalid_size')

        return value

class BaseSchema(Schema):
    OPTIONS_CLASS = BaseOpts

    @post_load
    def make_object(self, data):
        # this will depend on the Schema used, which has its object class in
        # the class Meta attributes
        #print('data....',data)
        decoding_class = self.opts.decoding_class
        return decoding_class(**data)

class DepositStatusSchema(BaseSchema):
    user_address = fields.String(missing=None)
    transaction_hash = fields.String(missing=None)

    class Meta:
        strict = True
        decoding_class = dict

class RawTransactionSchema(BaseSchema):
    chain_name = fields.String(missing=None)
    signed_data = fields.String(missing=None)

    class Meta:
        strict = True
        decoding_class = dict

class NonceSchema(BaseSchema):
    chain_name = fields.String(missing=None)
    user = fields.String(missing=None)

    class Meta:
        strict = True
        decoding_class = dict

class BalanceSchema(BaseSchema):
    user = fields.String(missing=None)
    class Meta:
        strict = True
        decoding_class = dict

class DepositLimitSchema(BaseSchema):
    class Meta:
        strict = True
        decoding_class = dict

class TokenSchema(BaseSchema):
    chain_name = fields.String(missing=None)
    user_address = AddressField(missing=None)
    decimals = fields.Integer(missing=None)
    total_suply = fields.Integer(missing=None)
    name = fields.String(missing=None)
    symbol = fields.String(missing=None)

    class Meta:
        strict = True
        decoding_class = dict
