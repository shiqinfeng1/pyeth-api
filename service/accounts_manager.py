# -*- coding: utf-8 -*-
import click
import sys
import os
import random
from ethereum import slogging
from ethereum import keys
from bitcoin import privtopub
import json
from binascii import hexlify, unhexlify
from service import constant 
from uuid import UUID
from rlp.utils import decode_hex
from ethereum.utils import sha3, is_string, encode_hex, remove_0x_head, to_string

log = slogging.get_logger("root")

def mk_random_privkey():
    k = hex(random.getrandbits(256))[2:-1].zfill(64)
    assert len(k) == 64
    return decode_hex(k)

def find_datadir():
    home = os.path.expanduser('~')
    if home == '~':  # Could not expand user path
        return None
    datadir = None

    if sys.platform == 'darwin':
        datadir = os.path.join(home, 'Library', 'Ethereum')
    # NOTE: Not really sure about cygwin here
    elif sys.platform == 'win32' or sys.platform == 'cygwin':
        datadir = os.path.join(home, 'AppData', 'Roaming', 'Ethereum')
    elif os.name == 'posix':
        datadir = os.path.join(home, '.ethereum')
    else:
        raise RuntimeError('Unsupported Operating System')

    if not os.path.isdir(datadir):
        return None
    return datadir


def find_keystoredir():
    datadir = find_datadir()
    if datadir is None:
        # can't find a data directory in the system
        return None
    keystore_path = os.path.join(datadir, 'keystore')
    if not os.path.exists(keystore_path):
        # can't find a keystore under the found data directory
        return None
    return keystore_path


class Account(object):
    """Represents an account.  """
    def __init__(self, keystore, password=None, path=None):
        """
        Args:
            keystore: the key store as a dictionary (as decoded from json)
            locked: `True` if the account is locked and neither private nor public keys can be
                      accessed, otherwise `False`
            path: absolute path to the associated keystore file (`None` for in-memory accounts)
        """
        if path is not None:
            path = os.path.abspath(path)

        self.keystore = keystore
        self.locked = True
        self.path = path
        self._privkey = None
        self._address = None

        try:
            self._address = unhexlify(self.keystore['address'])
        except KeyError:
            pass

        if password is not None:
            self.unlock(password)

    @classmethod
    def new(cls, password, key=None, uuid=None, path=None):
        """Create a new account.

        Note that this creates the account in memory and does not store it on disk.

        :param password: the password used to encrypt the private key
        :param key: the private key, or `None` to generate a random one
        :param uuid: an optional id
        """
        if key is None:
            key = mk_random_privkey()

        # [NOTE]: key and password should be bytes
        if not is_string(key):
            key = to_string(key)
        if not is_string(password):
            password = to_string(password)

        keystore = keys.make_keystore_json(key, password)
        if not is_string(uuid):
            uuid = to_string(uuid)
        keystore['id'] = uuid
        return Account(keystore, password, path)

    @classmethod
    def load(cls, path, password=None):
        """Load an account from a keystore file.

        Args:
            path: full path to the keyfile
            password: the password to decrypt the key file or `None` to leave it encrypted
        """
        with open(path) as f:
            keystore = json.load(f)
        if not keys.check_keystore_json(keystore):
            raise ValueError('Invalid keystore file')
        return Account(keystore, password, path=path)

    def dump(self, include_address=True, include_id=True):
        """Dump the keystore for later disk storage.

        The result inherits the entries `'crypto'` and `'version`' from `account.keystore`, and
        adds `'address'` and `'id'` in accordance with the parameters `'include_address'` and
        `'include_id`'.

        If address or id are not known, they are not added, even if requested.

        Args:
            include_address: flag denoting if the address should be included or not
            include_id: flag denoting if the id should be included or not
        """
        d = {}
        d['crypto'] = self.keystore['crypto']
        d['version'] = self.keystore['version']
        if include_address and self.address is not None:
            d['address'] = hexlify(self.address)
        if include_id and self.uuid is not None:
            d['id'] = self.uuid
        return json.dumps(d)

    def unlock(self, password):
        """Unlock the account with a password.

        If the account is already unlocked, nothing happens, even if the password is wrong.

        Raises:
            ValueError: (originating in ethereum.keys) if the password is wrong
            (and the account is locked)
        """
        if self.locked:
            try:
                self._privkey = keys.decode_keystore_json(self.keystore, password)
                self.locked = False
            except Exception,e:
                log.error("accout lock fail: {}. ".format(e.message))
                self.lock()


    def lock(self):
        """Relock an unlocked account.

        This method sets `account.privkey` to `None` (unlike `account.address` which is preserved).
        After calling this method, both `account.privkey` and `account.pubkey` are `None.
        `account.address` stays unchanged, even if it has been derived from the private key.
        """
        self._privkey = None
        self.locked = True

    @property
    def privkey(self):
        """The account's private key or `None` if the account is locked"""
        if not self.locked:
            return self._privkey
        return None

    @property
    def pubkey(self):
        """The account's public key or `None` if the account is locked"""
        if not self.locked:
            return privtopub(self.privkey)

        return None

    @property
    def address(self):
        """The account's address or `None` if the address is not stored in the key file and cannot
        be reconstructed (because the account is locked)
        """
        if self._address:
            pass
        elif 'address' in self.keystore:
            self._address = unhexlify(self.keystore['address'])
        elif not self.locked:
            self._address = keys.privtoaddr(self.privkey)
        else:
            return None
        return self._address

    @property
    def uuid(self):
        """An optional unique identifier, formatted according to UUID version 4, or `None` if the
        account does not have an id
        """
        try:
            return self.keystore['id']
        except KeyError:
            return None

    @uuid.setter
    def uuid(self, value):
        """Set the UUID. Set it to `None` in order to remove it."""
        if value is not None:
            self.keystore['id'] = value
        elif 'id' in self.keystore:
            self.keystore.pop('id')

    def sign_tx(self, tx):
        """Sign a Transaction with the private key of this account.

        If the account is unlocked, this is equivalent to ``tx.sign(account.privkey)``.

        Args:
            tx: the :class:`ethereum.transactions.Transaction` to sign

        Raises:
            ValueError: if the account is locked
        """
        if self.privkey:
            log.info('signing tx', tx=tx, account=self)
            tx.sign(self.privkey)
        else:
            raise ValueError('Locked account cannot sign tx')

    def __repr__(self):
        if self.address is not None:
            address = hexlify(self.address)
        else:
            address = '?'
        return '<Account(address={address}, id={id})>'.format(address=address, id=self.uuid)

class AccountManager(object):
   
    def __init__(self, keystore_path=None,admin_account=None):
        self.keystore_path = keystore_path
        self.accounts = {}
        self.admin_password = 0
        if self.keystore_path is None:
            self.keystore_path = find_keystoredir()
        if self.keystore_path is not None:

            for f in os.listdir(self.keystore_path):
                fullpath = os.path.join(self.keystore_path, f)
                if os.path.isfile(fullpath):
                    try:
                        with open(fullpath) as data_file:
                            data = json.load(data_file)
                            self.accounts[str(data['address']).lower()] = str(fullpath)
                    except (ValueError, KeyError, IOError) as ex:
                        # Invalid file - skip
                        if f.startswith('UTC--'):
                            # Should be a valid account file - warn user
                            msg = 'Invalid account file'
                            if isinstance(ex, IOError):
                                msg = 'Can not read account file'
                            log.warning('%s %s: %s', msg, fullpath, ex)

        if admin_account != None:
            self.admin_account = admin_account
        elif len(self.accounts):
            self.admin_account = '0x'+self.accounts.keys()[0]
        else:
            self.admin_account = None

    def set_admin_password(self, pwd):
        self.admin_password = pwd
        
    def get_admin_password(self):
        return self.admin_password

    def set_admin_account(self, old_address,address):
        assert isinstance(address,str)
        assert len(address) == 42 and address[:2]=='0x'
        
        password = click.prompt('Enter the password to unlock %s' % old_address, default='', hide_input=True,
                                confirmation_prompt=False, show_default=False)
        acc = Account.load(self.keystore_path+old_address,password)
        if acc.locked == False:
            self.admin_account = address
            acc.lock()
        else:
            print('set admin account fail.')

    def get_admin_account(self):
        return self.admin_account

    def address_in_keystore(self, address):
        if address is None:
            return False

        if address.startswith('0x'):
            address = address[2:]

        return address.lower() in self.accounts
    
    def add_account(self, account, store=True, include_address=True, include_id=True):
        """Add an account.

        If `store` is true the account will be stored as a key file at the location given by
        `account.path`. If this is `None` a :exc:`ValueError` is raised. `include_address` and
        `include_id` determine if address and id should be removed for storage or not.

        This method will raise a :exc:`ValueError` if the new account has the same UUID as an
        account already known to the service. Note that address collisions do not result in an
        exception as those may slip through anyway for locked accounts with hidden addresses.
        """
        log.info('adding account', account=account,path=account.path)
        if account.uuid is not None:
            for address in self.accounts.keys():
                with open(self.accounts[address]) as data_file:
                    data = json.load(data_file)
                    if len([acct for acct in self.accounts if data['id'] == account.uuid]) > 0:
                        log.error('could not add account (UUID collision)', uuid=account.uuid)
                        raise ValueError('Could not add account (UUID collision)')
        if store:
            if account.path is None:
                raise ValueError('Cannot store account without path')
            assert os.path.isabs(account.path), account.path
            if os.path.exists(account.path):
                log.error('File does already exist', path=account.path)
                raise IOError('File does already exist')
            assert account.path not in [path for path in self.accounts]
            try:
                directory = os.path.dirname(account.path)
                if not os.path.exists(directory):
                    os.makedirs(directory)
                with open(account.path, 'w') as f:
                    f.write(account.dump(include_address, include_id))
            except IOError as e:
                log.error('Could not write to file', path=account.path, message=e.strerror,
                          errno=e.errno)
                raise
        self.accounts[encode_hex(account._address)] = account.path
        print('after add new account: {} path:{}'.format(self.accounts.keys(),account.path))
        
    def get_account(self, address, password=None, password_file=None):
        """Find the keystore file for an account, unlock it and get the private key

        Args:
            address(str): The Ethereum address for which to find the keyfile in the system
            password(str): Mostly for testing purposes. A password can be provided
                           as the function argument here. If it's not then the
                           user is interactively queried for one.
        Returns
            str: The private key associated with the address
        """

        if address.startswith('0x'):
            address = address[2:]

        address = address.lower()

        if not self.address_in_keystore(address):
            raise ValueError('Keystore file not found for %s' % address)

        with open(self.accounts[address]) as data_file:
            data = json.load(data_file)

        # Since file was found prompt for a password if not already given
        if password_file:
            password = password_file.read().splitlines()[0]
        if password is None:
            password = click.prompt('Enter the password to unlock %s' % address, default='', hide_input=True,
                                confirmation_prompt=False, show_default=False)
        acc = Account(data, password, self.accounts[address])
        return acc

    def select_account(address, password=None, password_file=None):
        if not self.accounts:
            raise RuntimeError('No Ethereum accounts found in the user\'s system')

        if address.startswith('0x'):
            address = address[2:]

        if not self.address_in_keystore(address):
            # check if an address has been passed
            if address is not None:
                print("Account '{}' could not be found on the system. Aborting ...".format(
                    address))
                sys.exit(1)

            addresses = list(self.accounts.keys())
            formatted_addresses = [
                '[{:3d}] - 0x{}'.format(idx, addr)
                for idx, addr in enumerate(addresses)
            ]

            should_prompt = True

            print('The following accounts were found in your machine:')
            print('')
            print('\n'.join(formatted_addresses))
            print('')

            while should_prompt:
                idx = click.prompt('Select one of them by index to continue', type=int)

                if idx >= 0 and idx < len(addresses):
                    should_prompt = False
                else:
                    print("\nError: Provided index '{}' is out of bounds\n".format(idx))

            address = addresses[idx]

        if password_file:
            password = password_file.read().splitlines()[0]
        if password:
            try:
                acc = self.get_account(address, password)
            except ValueError:
                # ValueError exception raised if the password is incorrect
                print('Incorrect password for {} in file. Aborting ...'.format(address))
                sys.exit(1)
        else:
            unlock_tries = 3
            while True:
                try:
                    acc = self.get_account(address)
                    break
                except ValueError:
                    # ValueError exception raised if the password is incorrect
                    if unlock_tries == 0:
                        print(
                            'Exhausted passphrase unlock attempts for {}. Aborting ...'
                            .format(address)
                        )
                        sys.exit(1)

                    print(
                        'Incorrect passphrase to unlock the private key. {} tries remaining. '
                        'Please try again or kill the process to quit. '
                        'Usually Ctrl-c.'.format(unlock_tries)
                    )
                    unlock_tries -= 1

        return acc