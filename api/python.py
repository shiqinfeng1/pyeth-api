# -*- coding: utf-8 -*-
import os
from ethereum.utils import normalize_address
from binascii import hexlify, unhexlify
from service.utils import (
    address_encoder,
    address_decoder,
)
from uuid import uuid4
from service import constant,accounts_manager
from service.accounts_manager import Account,find_keystoredir
from ethereum.utils import encode_hex


class PYETHAPI(object):
    """ CLI interface. """

    def __init__(self,blockchain_service):
        print('init pyeth-api ...')
        self.blockchain_service = blockchain_service

    @property
    def adminAddress(self):
        return self.blockchain_service.adminAddress
    #raise NotImplementedError()

    def _get_chain_proxy(self,chain_name):
        assert chain_name in self.blockchain_service.blockchain_proxy.keys()
        _proxy = self.blockchain_service.blockchain_proxy[chain_name]
        return _proxy

    def _get_contract_address(self,chain_name,contract_name): 
        _proxy = self._get_chain_proxy(chain_name)
        _contract_proxy = _proxy.attach_contract(contract_name)
        return _contract_proxy.address if _contract_proxy != None else None


    """新建区块链代理"""
    def new_blockchain_proxy(self, chain_name,endpoint,keystore_path):
        assert keystore_path != None
        if chain_name not in self.blockchain_service.blockchain_proxy.keys():
            _proxy = self.blockchain_service.new_blockchain_proxy(
                chain_name, endpoint, keystore_path)
        return _proxy

    """查询当前区块链所有代理"""
    def blockchain_proxy_list(self):
        proxy_list = list(self.blockchain_service.blockchain_proxy.keys())
        return proxy_list
        
    """设置管理员账户"""
    def set_admin_account(self,chain_name,old_address,admin_address):
        _proxy = self._get_chain_proxy(chain_name)
        _proxy.account_manager.set_admin_account(old_address,admin_addess)

    """创建新账户"""
    def new_account(self, chain_name, password=None, key=None):
        assert isinstance(key,str) and len(key)==64
        id_ = uuid4()
        _proxy = self._get_chain_proxy(chain_name)

        if password is None:
            password = ''
        account = Account.new(password, key=key, uuid=id_)
        account.path = os.path.join(_proxy.account_manager.keystore_path, '0x'+encode_hex(account.address))
        try:
            _proxy.account_manager.add_account(account) 
        except IOError:
            print('Could not write keystore file. Make sure you have write permission in the '
                    'configured directory and check the log for further information.')
            sys.exit(1)
        else:
            print('Account creation successful')
            print('  Address: {}'.format(encode_hex(account.address)))
            print('       Id: {}'.format(account.uuid))

    """查询当前keystore下所有账户"""
    def eth_accounts_list(self,chain_name): 
        _proxy = self._get_chain_proxy(chain_name)
        return list(_proxy.account_manager.accounts.keys())

    """原生币转账"""
    def transfer_currency(self,chain_name,sender,to,amount):
        _proxy = self._get_chain_proxy(chain_name)
        amount = amount * constant.WEI_TO_ETH
        _proxy.transfer_currency(sender,to,amount)
    
    """token转账"""
    def transfer_token(self,chain_name,contract_address,sender,to,amount,is_erc223=False):
        _proxy = self._get_chain_proxy(chain_name)
        contract_proxy = _proxy.attach_contract(
            'Token',
            contract_file='Token.sol',
            contract_address=contract_address,
            attacher=sender,
        )
        block_number = _proxy.block_number()
        #由于pythpn版本以太坊暂时无法处理同名函数, 暂时通过flag来区分
        if is_erc223 == True:
            txhash = contract_proxy.transfer(to,amount*constant.ATM_DECIMALS,'')
        else:
            txhash = contract_proxy.transfer(to,amount*constant.ATM_DECIMALS)

        _proxy.poll_contarct_transaction_result(txhash,block_number,contract_proxy,'Transfer',to)

class POLLING_EVENTS(object):
    def __init__(
            self
            ):
        self.polling_events = dict()
        self.is_stopped = false
        self.polling_delay = 3
        
    def run(self,chain_name):
        _proxy = self._get_chain_proxy(chain_name)
        print('satrt monitor retweet...')
        while not self.is_stopped:
            gevent.sleep(self.polling_delay)
            
            ATMToken_contract_proxy = ethereum_proxy.attach_contract('ATMToken')

            block_number = ethereum_proxy.block_number()
            txhash = ATMToken_contract_proxy.transfer(
                _to,lock_amount*constant.ATM_DECIMALS)

            ethereum_proxy.poll_contarct_transaction_result(
                txhash,block_number,ATMToken_contract_proxy,'Transfer',_to)

        
class PYETHAPI_ATMCHAIN(PYETHAPI):
    
    polling_events = POLLING_EVENTS()

    def __init__(self,blockchain_service):
        print('init PYETHAPI_ATMCHAIN ...')
        super(PYETHAPI_ATMCHAIN, self).__init__(blockchain_service)
    
    def new_blockchain_proxy(self, chain_name,endpoint,keystore_path):
        _proxy = super().new_blockchain_proxy(chain_name,endpoint,keystore_path)

        polling = Greenlet.spawn(
            polling_events.run,
            chain_name
        ) 
        return _proxy

    def register_polling_event(self, chain_name, contract_name, event_name, *args):
        polling_events.polling_events[chain_name] = {
            contract_name+'_'+event_name : [0, contract_name, event_name, *args]
        }

    def ATM_accounts_list(self): 
        contract_Addresses=dict()
        ethereum_proxy = self._get_chain_proxy('ethereum')
        atmchain_proxy = self._get_chain_proxy('atmchain')
        ERC20Token_ethereum_address = self._get_contract_address(
            'ethereum',
            'ATMToken',
            )
        TokenExchange_ethereum_address = self._get_contract_address(
            'ethereum',
            'TokenExchange',
            )
        ERC223Token_atmchain_address = self._get_contract_address(
            'atmchain',
            'ERC223Token',
            )
        contract_Addresses['ATMToken_address'] = address_encoder(ERC20Token_ethereum_address) if ERC20Token_ethereum_address != None else 'NOT deployed'
        contract_Addresses['TokenExchange_address'] = address_encoder(TokenExchange_ethereum_address) if TokenExchange_ethereum_address != None else 'NOT deployed'
        contract_Addresses['ERC223Token_address'] = address_encoder(ERC223Token_atmchain_address) if ERC223Token_atmchain_address != None else 'NOT deployed'

        return contract_Addresses,self.eth_accounts_list('ethereum'),self.eth_accounts_list('atmchain')

    def deploy_ATM_contract(self,atm_address=None): 
        
        ethereum_proxy = self._get_chain_proxy('ethereum')
        ethereum_sender = ethereum_proxy.account_manager.admin_account
        atmchain_proxy = self._get_chain_proxy('atmchain')
        atmchain_sender = atmchain_proxy.account_manager.admin_account

        ERC223Token_atmchain_owner = atmchain_proxy.deploy_contract( 
            atmchain_sender,
            'ERC223Token.sol', 'ERC223Token',
            (100000,'REX',8,'REX Token'),
            )

        if atm_address == None:
            ERC20Token_ethereum_owner = ethereum_proxy.deploy_contract( 
                ethereum_sender,
                'ATMToken.sol', 'ATMToken',
                )
            atm_address = ERC20Token_ethereum_owner.address
        else:
            ethereum_proxy = self._get_chain_proxy('ethereum')
            ERC20Token_ethereum_owner = ethereum_proxy.attach_contract(
                'ATMToken.sol','ATMToken',
                contract_address=atm_address,
                attacher=ethereum_sender,
                )

        TokenExchange_ethereum_owner = ethereum_proxy.deploy_contract( 
            ethereum_sender, 
            'TokenExchange.sol', 'TokenExchange',
            (hexlify(atm_address),)
            )


"""
    def lock_ATM(self,from_chain,to_chain,advertiser,lock_amount):
        
        ethereum_proxy = self._get_chain_proxy(from_chain)
        atmchain_proxy = self._get_chain_proxy(to_chain)

        ERC20Token_ethereum_owner = ethereum_proxy.attach_contract(
            'ATMToken',
            attacher=ethereum_proxy.account_manager.admin_account,
            )
        TokenExchange_ethereum_owner = ethereum_proxy.attach_contract(
            'TokenExchange',
            attacher=ethereum_proxy.account_manager.admin_account,
            )
        ERC20Token_ethereum_advister = ethereum_proxy.attach_contract(
            'ATMToken',
            attacher=advertiser,
            )
        ERC223Token_atmchain_owner = atmchain_proxy.attach_contract(
            'ERC223Token',
            attacher=ethereum_proxy.account_manager.admin_account,
            )
        block_number = ethereum_proxy.block_number()
        txhash = ERC20Token_ethereum_advister.transfer(
            TokenExchange_ethereum_owner.address,lock_amount*constant.ATM_DECIMALS)
        ethereum_proxy.poll_contarct_transaction_result(
            txhash,block_number,ERC20Token_ethereum_advister,'Transfer',TokenExchange_ethereum_owner.address)

        block_number = ethereum_proxy.block_number()
        txhash = TokenExchange_ethereum_owner.lockToken(
            normalize_address(advertiser),lock_amount*constant.ATM_DECIMALS)
        ethereum_proxy.poll_contarct_transaction_result(
            txhash,block_number,TokenExchange_ethereum_owner,'LogLockToken',advertiser)

        block_number = atmchain_proxy.block_number()
        txhash = ERC223Token_atmchain_owner.mint(advertiser,lock_amount)
        atmchain_proxy.poll_contarct_transaction_result(
            txhash,block_number,ERC223Token_atmchain_owner,'Minted',advertiser) 

    def settle_ATM(self,from_chain,to_chain,scaner,settle_amount):
        
        ethereum_proxy = self._get_chain_proxy(from_chain)
        atmchain_proxy = self._get_chain_proxy(to_chain)

        ERC223Token_atmchain_owner = atmchain_proxy.attach_contract(
            'ERC223Token',
            attacher=ethereum_proxy.account_manager.admin_account,
            )

        if settle_amount > ERC223Token_atmchain_owner.balanceOf(scaner)/constant.ATM_DECIMALS:
            raise ValueError('insufficient token balance of {}'.format(scaner))

        ERC223Token_atmchain_scaner = atmchain_proxy.attach_contract(
            'ERC223Token',
            attacher=scaner,
            )
        TokenExchange_ethereum_owner = ethereum_proxy.attach_contract(
            'TokenExchange',
            attacher=ethereum_proxy.account_manager.admin_account,
            )

        block_number = atmchain_proxy.block_number()
        txhash = ERC223Token_atmchain_scaner.transfer(
            constant.BLACKHOLE_ADDRESS,settle_amount*constant.ATM_DECIMALS,'')
        atmchain_proxy.poll_contarct_transaction_result(
            txhash,block_number,ERC223Token_atmchain_scaner,'Transfer',scaner,constant.BLACKHOLE_ADDRESS)

        block_number = ethereum_proxy.block_number()
        txhash = TokenExchange_ethereum_owner.settleToken(scaner,settle_amount*constant.ATM_DECIMALS)
        ethereum_proxy.poll_contarct_transaction_result(txhash,block_number,TokenExchange_ethereum_owner,'LogSettleToken',scaner)
"""
    def query_currency_balance(self,chain_name,account):
        _proxy = self._get_chain_proxy(chain_name)

        temp = _proxy.balance(address_decoder(account))
        result = float(temp)/constant.WEI_TO_ETH
        return result

    def query_atmchain_balance(self,src_chain,dest_chain,account):

        result=dict()
        ethereum_proxy = self._get_chain_proxy(src_chain)
        atmchain_proxy = self._get_chain_proxy(dest_chain)

        ERC20Token_ethereum = ethereum_proxy.attach_contract(
            'ATMToken'
            )

        ERC223Token_atmchain = atmchain_proxy.attach_contract(
            'ERC223Token'
            )

        temp = ethereum_proxy.balance(address_decoder(account))
        result['ETH balance in ethereum'] = float(temp)/constant.WEI_TO_ETH

        temp = ERC20Token_ethereum.balanceOf(account) if ERC20Token_ethereum != None else 0
        result['ATM balance in ethereum'] = float(temp)/constant.ATM_DECIMALS 
    
        temp = atmchain_proxy.balance(address_decoder(account))
        result['ETH balance in atmchain'] = float(temp)/constant.WEI_TO_ETH
        
        temp = ERC223Token_atmchain.balanceOf(account) if ERC223Token_atmchain != None else 0
        result['ATM balance in atmchain'] = float(temp)/constant.ATM_DECIMALS
    
        return result
