
from ethereum import _solidity
DEFAULT_POLL_TIMEOUT = 180
solidity = _solidity.get_solidity()  # pylint: disable=invalid-name

def deploy_contract(privatekey, contract_file, contract_name, constructor_parameters=None):
    contract_path = get_contract_path(contract_file)
    contracts = _solidity.compile_file(contract_path, libraries=dict())

    log.info(
        'Deploying "%s" contract',
        contract_file,
    )
    jsonrpc_client = JSONRPCClient(
        privkey=privatekey,
        host=self.host,
        port=self.port,
        print_communication=True,
    )

    proxy = jsonrpc_client.deploy_solidity_contract(
        privatekey_to_address(privatekey),
        contract_name,
        contracts,
        dict(),
        constructor_parameters,
        contract_path=contract_path,
        gasprice=default_gasprice,
        timeout=DEFAULT_POLL_TIMEOUT,
    )
    log.info(
        'Address is "%s" .',
        proxy.address,
    )
    return proxy.address