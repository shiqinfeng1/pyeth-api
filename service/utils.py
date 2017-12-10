# -*- coding: utf-8 -*-
import os
from coincurve import PrivateKey
from binascii import hexlify, unhexlify
from sha3 import keccak_256

def timeout_two_stage(retries, timeout1, timeout2):
    """ Timeouts generator with a two stage strategy

    Timeouts start spaced by `timeout1`, after `retries` increase
    to `timeout2` which is repeated indefinitely.
    """
    for _ in xrange(retries):
        yield timeout1
    while True:
        yield timeout2

def sha3(data):
    """
    Raises:
        RuntimeError: If Keccak lib initialization failed, or if the function
        failed to compute the hash.

        TypeError: This function does not accept unicode objects, they must be
        encoded prior to usage.
    """
    return keccak_256(data).digest()

def get_project_root():
    return os.path.dirname(raiden.__file__)

def get_contract_path(contract_name):
    contract_path = os.path.join(
        get_project_root(),
        'smart_contracts',
        contract_name
    )
    return os.path.realpath(contract_path)

def address_decoder(addr):
    if addr[:2] == '0x':
        addr = addr[2:]

    addr = unhexlify(addr)
    assert len(addr) in (20, 0)
    return addr


def address_encoder(address):
    assert len(address) in (20, 0)
    return '0x' + hexlify(address)


def block_tag_encoder(val):
    if isinstance(val, int):
        return hex(val).rstrip('L')

    assert val in ('latest', 'pending')
    return '0x' + hexlify(val)

def data_encoder(data, length=None):
    data = hexlify(data)
    length = length or 0
    return '0x' + data.rjust(length * 2, '0')


def data_decoder(data):
    assert data[:2] == '0x'
    data = data[2:]  # remove 0x
    data = unhexlify(data)
    return data


def quantity_decoder(data):
    assert data[:2] == '0x'
    data = data[2:]  # remove 0x
    return int(data, 16)


def quantity_encoder(i):
    """Encode integer quantity `data`."""
    return hex(i).rstrip('L')

def topic_encoder(topic):
    assert isinstance(topic, (int, long))

    if topic == 0:
        return '0x'

    topic = hex(topic).rstrip('L')
    if len(topic) % 2:
        topic = '0x0' + topic[2:]
    return topic

def topic_decoder(topic):
    return int(topic[2:], 16)

def isaddress(data):
    return isinstance(data, (bytes, bytearray)) and len(data) == 20

def pex(data):
    return str(data).encode('hex')[:8]

def privatekey_to_address(private_key_bin):
    private_key = PrivateKey(private_key_bin)
    pubkey = private_key.public_key.format(compressed=False)
    return publickey_to_address(pubkey)

def publickey_to_address(publickey):
    return sha3(publickey[1:])[12:]

def make_address():
    return bytes(''.join(random.choice(LETTERS) for _ in range(20)))


def make_privkey_address():
    private_key_bin = sha3(''.join(random.choice(LETTERS) for _ in range(20)))
    privkey = PrivateKey(private_key_bin)
    pubkey = privkey.public_key.format(compressed=False)
    address = publickey_to_address(pubkey)
    return privkey, address
