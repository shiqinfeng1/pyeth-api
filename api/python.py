import os
from ethereum.utils import normalize_address
from binascii import hexlify, unhexlify

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

    def _get_chain_proxy(self):
        assert 'ethereum' in self.blockchain_service.blockchain_proxy.keys()
        assert 'quorum' in self.blockchain_service.blockchain_proxy.keys()
            
        ethereum_proxy = self.blockchain_service.blockchain_proxy['ethereum']
        quorum_proxy = self.blockchain_service.blockchain_proxy['quorum']
        return ethereum_proxy,quorum_proxy

    def accounts_list(self): 
        contract_Addresses=dict()
        ethereum_proxy,quorum_proxy = self._get_chain_proxy()
        ERC20Token_ethereum_owner = ethereum_proxy.get_contract_proxy(
            ethereum_proxy.account_manager.admin_account,
            'ATMToken'
            )
        TokenExchange_ethereum_owner = ethereum_proxy.get_contract_proxy(
            ethereum_proxy.account_manager.admin_account,
            'TokenExchange'
            )
        ERC223Token_quorum_owner = quorum_proxy.get_contract_proxy(
            ethereum_proxy.account_manager.admin_account,
            'ERC223Token'
            )
        contract_Addresses['ATMToken_address'] = ERC20Token_ethereum_owner.address if ERC20Token_ethereum_owner != None else 'NOT deployed'
        contract_Addresses['TokenExchange_address'] = TokenExchange_ethereum_owner.address if TokenExchange_ethereum_owner != None else 'NOT deployed'
        contract_Addresses['ERC223Token_address'] = ERC223Token_quorum_owner.address if ERC223Token_quorum_owner != None else 'NOT deployed'

        return contract_Addresses,list(ethereum_proxy.account_manager.accounts.keys()),list(quorum_proxy.account_manager.accounts.keys())

    def deploy_contract(self,atm_address=None): 
        
        ethereum_proxy,quorum_proxy = self._get_chain_proxy()

        ERC223Token_quorum_owner = quorum_proxy.deploy_contract( 
            quorum_proxy.account_manager.admin_account, 
            'ERC223Token.sol', 'ERC223Token',
            (100000,'REX',18,'REX Token'),
            )

        if atm_address == None:
            ERC20Token_ethereum_owner = ethereum_proxy.deploy_contract( 
                ethereum_proxy.account_manager.admin_account, 
                'ATMToken.sol', 'ATMToken',
                )
            atm_address = ERC20Token_ethereum_owner.address
        else:
            ERC20Token_ethereum_owner = ethereum_proxy.attach_contract(
                ethereum_proxy.account_manager.admin_account, 
                atm_address,
                'ATMToken.sol','ATMToken',
                )
        TokenExchange_ethereum_owner = ethereum_proxy.deploy_contract( 
            ethereum_proxy.account_manager.admin_account, 
            'TokenExchange.sol', 'TokenExchange',
            (hexlify(atm_address),)
            )

        
    def lock_token(self,adviser,lock_amount):
        
        ethereum_proxy,quorum_proxy = self._get_chain_proxy()

        ERC20Token_ethereum_owner = ethereum_proxy.get_contract_proxy(
            ethereum_proxy.account_manager.admin_account,
            'ATMToken'
            )
        TokenExchange_ethereum_owner = ethereum_proxy.get_contract_proxy(
            ethereum_proxy.account_manager.admin_account,
            'TokenExchange'
            )
        ERC20Token_ethereum_advister = ethereum_proxy.get_contract_proxy(
            adviser,
            'ATMToken'
            )
        ERC223Token_quorum_owner = quorum_proxy.get_contract_proxy(
            ethereum_proxy.account_manager.admin_account,
            'ERC223Token'
            )
        block_number = ethereum_proxy.block_number()
        txhash = ERC20Token_ethereum_advister.transfer(
            TokenExchange_ethereum_owner.address,lock_amount*WEI_TO_ETH)
        ethereum_proxy.poll_contarct_transaction_result(
            txhash,block_number,ERC20Token_ethereum_advister,'Transfer',TokenExchange_ethereum_owner.address)

        block_number = ethereum_proxy.block_number()
        txhash = TokenExchange_ethereum_owner.lockToken(
            normalize_address(adviser),lock_amount*WEI_TO_ETH)
        ethereum_proxy.poll_contarct_transaction_result(
            txhash,block_number,TokenExchange_ethereum_owner,'LogLockToken',advister)

        block_number = quorum_proxy.block_number()
        txhash = ERC223Token_quorum_owner.mint(advister,lock_amount)
        quorum_proxy.poll_contarct_transaction_result(
            txhash,block_number,ERC223Token_quorum_owner,'Minted',advister) 

    def settle_token(self,scaner,settle_amount):
        
        ethereum_proxy,quorum_proxy = self._get_chain_proxy()

        ERC223Token_quorum_owner = quorum_proxy.get_contract_proxy(
            ethereum_proxy.account_manager.admin_account,
            'ERC223Token'
            )

        if settle_amount > ERC223Token_quorum_owner.balanceOf(scaner)/WEI_TO_ETH:
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
            BLACKHOLE_ADDRESS,settle_amount*WEI_TO_ETH,'')
        quorum_proxy.poll_contarct_transaction_result(
            txhash,block_number,ERC223Token_quorum_scaner,'Transfer',scaner,BLACKHOLE_ADDRESS)

        block_number = ethereum_proxy.block_number()
        txhash = TokenExchange_ethereum_owner.settleToken(scaner,settle_amount*WEI_TO_ETH)
        ethereum_proxy.poll_contarct_transaction_result(txhash,block_number,TokenExchange_ethereum_owner,'LogSettleToken',scaner)

    def query_balance(self,account):

        result=dict()
        ethereum_proxy,quorum_proxy = self._get_chain_proxy()

        ERC20Token_ethereum_owner = ethereum_proxy.get_contract_proxy(
            ethereum_proxy.account_manager.admin_account,
            'ATMToken'
            )
        ERC223Token_quorum_owner = quorum_proxy.get_contract_proxy(
            ethereum_proxy.account_manager.admin_account,
            'ERC223Token'
            )

        temp = ethereum_proxy.balance(address_decoder(account))
        result['eth_b'] = temp/WEI_TO_ETH+temp%WEI_TO_ETH

        temp = ERC20Token_ethereum_owner.balanceOf(account)
        result['eth_atm_b'] = temp/WEI_TO_ETH+temp%WEI_TO_ETH
    
        temp = quorum_proxy.balance(address_decoder(addr))
        result['quo_b'] = temp/WEI_TO_ETH+temp%WEI_TO_ETH
        
        temp = ERC223Token_quorum_owner.balanceOf(addr)
        result['quo_atm_b'] = temp/WEI_TO_ETH+temp%WEI_TO_ETH
    
        return result