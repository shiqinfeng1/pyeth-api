import os
from ethereum.utils import normalize_address
from binascii import hexlify, unhexlify
from service.utils import (
    address_encoder,
    address_decoder,
)

from service import constant

class PYETHAPI(object):
    """ CLI interface. """

    def __init__(self,blockchain_service):
        print('init pyeth-api ...')
        self.blockchain_service = blockchain_service

    @property
    def adminAddress(self):
        return self.blockchain_service.adminAddress
    #raise NotImplementedError()

    def new_blockchain_proxy(self, chain_name,host,port):
        assert chain_name in ['ethereum', 'quorum']
        if chain_name not in self.blockchain_service.blockchain_proxy.keys():
            ethereum_proxy = self.blockchain_service.new_blockchain_proxy(
                chain_name, host, port, os.getcwd()+'/pyethapi/keystore')
        return ethereum_proxy

    def blockchain_proxy_list(self):
        proxy_list = list(self.blockchain_service.blockchain_proxy.keys())
        return proxy_list

    def _get_chain_proxy(self,chain_name):
        assert chain_name in self.blockchain_service.blockchain_proxy.keys()
        _proxy = self.blockchain_service.blockchain_proxy[chain_name]
        return _proxy

    def eth_accounts_list(self,chain_name): 
        _proxy = self._get_chain_proxy(chain_name)
        return list(_proxy.account_manager.accounts.keys())

    def _deploy_contract(self, 
        sender, chain_name, contract_file, contract_name,
        constructor_parameters=tuple(),
        password=None):

        _proxy = self._get_chain_proxy(chain_name)
        contract_proxy = _proxy.deploy_contract( 
            sender, 
            contract_file, contract_name,
            constructor_parameters,
            password,
            )
        return contract_proxy

    def _attach_contract(
        sender, 
        chain_name,
        contract_address,
        contract_file,contract_name):
        _proxy = self._get_chain_proxy(chain_name)
        contract_proxy = _proxy.attach_contract(
                sender, 
                contract_address,
                contract_file,contract_name,
                )
        return contract_proxy

    def _get_contract_address(self,chain_name,contract_name,readonly=True): 
        _proxy = self._get_chain_proxy(chain_name)
        _contract_proxy = _proxy.get_contract_proxy(
            chain_name,
            _proxy.account_manager.admin_account,
            contract_name,
            readonly,
            )
        return _contract_proxy.address if _contract_proxy != None else None

    def _transfer_eth(self,chain_name,sender,to,amount):
        _proxy = self._get_chain_proxy(chain_name)

class PYETHAPI_ATMCHAIN(PYETHAPI):
    def accounts_list(self): 
        contract_Addresses=dict()
        ethereum_proxy = self._get_chain_proxy('ethereum')
        quorum_proxy = self._get_chain_proxy('quorum')
        ERC20Token_ethereum_address = self._get_contract_address(
            'ethereum',
            'ATMToken',
            )
        TokenExchange_ethereum_address = self._get_contract_address(
            'ethereum',
            'TokenExchange',
            )
        ERC223Token_quorum_address = self._get_contract_address(
            'quorum',
            'ERC223Token',
            )
        contract_Addresses['ATMToken_address'] = address_encoder(ERC20Token_ethereum_address) if ERC20Token_ethereum_address != None else 'NOT deployed'
        contract_Addresses['TokenExchange_address'] = address_encoder(TokenExchange_ethereum_address) if TokenExchange_ethereum_address != None else 'NOT deployed'
        contract_Addresses['ERC223Token_address'] = address_encoder(ERC223Token_quorum_address) if ERC223Token_quorum_address != None else 'NOT deployed'

        return contract_Addresses,self.eth_accounts_list('ethereum'),self.eth_accounts_list('quorum')

    def deploy_ATM_contract(self,atm_address=None): 
        
        ethereum_proxy = self._get_chain_proxy('ethereum')
        ethereum_sender = ethereum_proxy.account_manager.admin_account
        quorum_proxy = self._get_chain_proxy('quorum')
        quorum_sender = quorum_proxy.account_manager.admin_account

        ERC223Token_quorum_owner = self._deploy_contract( 
            quorum_sender, 
            'quorum',
            'ERC223Token.sol', 'ERC223Token',
            (100000,'REX',8,'REX Token'),
            )

        if atm_address == None:
            ERC20Token_ethereum_owner = self._deploy_contract( 
                ethereum_sender, 
                'ethereum',
                'ATMToken.sol', 'ATMToken',
                )
            atm_address = ERC20Token_ethereum_owner.address
        else:
            ERC20Token_ethereum_owner = self._attach_contract(
                ethereum_sender, 
                'ethereum',
                atm_address,
                'ATMToken.sol','ATMToken',
                )
        TokenExchange_ethereum_owner = self._deploy_contract( 
            ethereum_sender, 
            'ethereum',
            'TokenExchange.sol', 'TokenExchange',
            (hexlify(atm_address),)
            )

    def transfer_eth(self,chain_name,sender,to,amount):
        self._transfer_eth(
            chain_name,
            sender,
            to,
        )
    def transfer_ATM(self,chain_name,erctoken_name,sender,to,amount,is_erc223=False):
        _proxy = self._get_chain_proxy(chain_name)
        contract_proxy = _proxy.get_contract_proxy(
            sender,
            chain_name,
            erctoken_name
        )
        block_number = _proxy.block_number()
        if is_erc223 == True:
            txhash = contract_proxy.transfer(to,amount*constant.ATM_DECIMALS,'')
        else:
            txhash = contract_proxy.transfer(to,amount*constant.ATM_DECIMALS)   

        _proxy.poll_contarct_transaction_result(txhash,block_number,contract_proxy,'Transfer',to)

    def lock_ATM(self,from_chain,to_chain,advertiser,lock_amount):
        
        ethereum_proxy = self._get_chain_proxy(from_chain)
        quorum_proxy = self._get_chain_proxy(to_chain)

        ERC20Token_ethereum_owner = ethereum_proxy.get_contract_proxy(
            ethereum_proxy.account_manager.admin_account,
            'ATMToken'
            )
        TokenExchange_ethereum_owner = ethereum_proxy.get_contract_proxy(
            ethereum_proxy.account_manager.admin_account,
            'TokenExchange'
            )
        ERC20Token_ethereum_advister = ethereum_proxy.get_contract_proxy(
            advertiser,
            'ATMToken'
            )
        ERC223Token_quorum_owner = quorum_proxy.get_contract_proxy(
            ethereum_proxy.account_manager.admin_account,
            'ERC223Token'
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

        block_number = quorum_proxy.block_number()
        txhash = ERC223Token_quorum_owner.mint(advertiser,lock_amount)
        quorum_proxy.poll_contarct_transaction_result(
            txhash,block_number,ERC223Token_quorum_owner,'Minted',advertiser) 

    def settle_ATM(self,from_chain,to_chain,scaner,settle_amount):
        
        ethereum_proxy = self._get_chain_proxy(from_chain)
        quorum_proxy = self._get_chain_proxy(to_chain)

        ERC223Token_quorum_owner = quorum_proxy.get_contract_proxy(
            ethereum_proxy.account_manager.admin_account,
            'ERC223Token'
            )

        if settle_amount > ERC223Token_quorum_owner.balanceOf(scaner)/constant.ATM_DECIMALS:
            raise ValueError('insufficient token balance of {}'.format(scaner))

        ERC223Token_quorum_scaner = quorum_proxy.get_contract_proxy(
            scaner,
            'ERC223Token'
            )
        TokenExchange_ethereum_owner = ethereum_proxy.get_contract_proxy(
            ethereum_proxy.account_manager.admin_account,
            'TokenExchange'
            )

        block_number = quorum_proxy.block_number()
        txhash = ERC223Token_quorum_scaner.transfer(
            constant.BLACKHOLE_ADDRESS,settle_amount*constant.ATM_DECIMALS,'')
        quorum_proxy.poll_contarct_transaction_result(
            txhash,block_number,ERC223Token_quorum_scaner,'Transfer',scaner,constant.BLACKHOLE_ADDRESS)

        block_number = ethereum_proxy.block_number()
        txhash = TokenExchange_ethereum_owner.settleToken(scaner,settle_amount*constant.ATM_DECIMALS)
        ethereum_proxy.poll_contarct_transaction_result(txhash,block_number,TokenExchange_ethereum_owner,'LogSettleToken',scaner)

    def query_balance(self,src_chain,dest_chain,account):

        result=dict()
        ethereum_proxy = self._get_chain_proxy(src_chain)
        quorum_proxy = self._get_chain_proxy(dest_chain)

        ERC20Token_ethereum_owner = ethereum_proxy.get_contract_proxy(
            ethereum_proxy.account_manager.admin_account,
            'ATMToken',
            '123456',
            )

        ERC223Token_quorum_owner = quorum_proxy.get_contract_proxy(
            ethereum_proxy.account_manager.admin_account,
            'ERC223Token',
            '123456',
            )

        temp = ethereum_proxy.balance(address_decoder(account))
        result['ETH balance in ethereum'] = float(temp)/constant.WEI_TO_ETH

        temp = ERC20Token_ethereum_owner.balanceOf(account) if ERC20Token_ethereum_owner != None else 0
        result['ATM balance in ethereum'] = float(temp)/constant.ATM_DECIMALS 
    
        temp = quorum_proxy.balance(address_decoder(account))
        result['ETH balance in quorum'] = float(temp)/constant.WEI_TO_ETH
        
        temp = ERC223Token_quorum_owner.balanceOf(account) if ERC223Token_quorum_owner != None else 0
        result['ATM balance in quorum'] = float(temp)/constant.ATM_DECIMALS
    
        return result

class PYETHAPI_ATMCHAIN_REWARDS_PLAN(PYETHAPI_ATMCHAIN):
    pass
