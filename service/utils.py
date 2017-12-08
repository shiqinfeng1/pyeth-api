import os
from coincurve import PrivateKey

def get_project_root():
    return os.path.dirname(raiden.__file__)

def get_contract_path(contract_name):
    contract_path = os.path.join(
        get_project_root(),
        'smart_contracts',
        contract_name
    )
    return os.path.realpath(contract_path)

# 检查是否是eth账户地址
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
