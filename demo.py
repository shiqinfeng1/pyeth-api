import  rpc.util

def _token_addresses(
        token_amount,
        number_of_tokens,
        deploy_service,
        blockchain_services,
        register):

    result = list()
    for _ in range(number_of_tokens):
        if register:
            token_address = deploy_service.deploy_and_register_token(
                contract_name='HumanStandardToken',
                contract_file='HumanStandardToken.sol',
                constructor_parameters=(token_amount, 'raiden', 2, 'Rd'),
            )
            result.append(token_address)
        else:
            token_address = deploy_service.deploy_contract(
                contract_name='HumanStandardToken',
                contract_file='HumanStandardToken.sol',
                constructor_parameters=(token_amount, 'raiden', 2, 'Rd'),
            )
            result.append(token_address)

        # only the creator of the token starts with a balance (deploy_service),
        # transfer from the creator to the other nodes
        for transfer_to in blockchain_services:
            deploy_service.token(token_address).transfer(
                privatekey_to_address(transfer_to.private_key),
                token_amount // len(blockchain_services),
            )

    return result

def _jsonrpc_services(
        deploy_key,
        private_keys,
        verbose,
        poll_timeout,
        rpc_port,
        registry_address=None):

    host = '0.0.0.0'
    print_communication = verbose > 6
    deploy_client = JSONRPCClient(
        host=host,
        port=rpc_port,
        privkey=deploy_key,
        print_communication=print_communication,
    )

    # we cannot instantiate BlockChainService without a registry, so first
    # deploy it directly with a JSONRPCClient
    if registry_address is None:
        address = privatekey_to_address(deploy_key)
        patch_send_transaction(deploy_client)
        patch_send_message(deploy_client)

        registry_path = get_contract_path('Registry.sol')
        registry_contracts = compile_file(registry_path, libraries=dict())

        log.info('Deploying registry contract')
        registry_proxy = deploy_client.deploy_solidity_contract(
            address,
            'Registry',
            registry_contracts,
            dict(),
            tuple(),
            contract_path=registry_path,
            gasprice=default_gasprice,
            timeout=poll_timeout,
        )
        registry_address = registry_proxy.address

    deploy_blockchain = BlockChainService(
        deploy_key,
        registry_address,
        host,
        deploy_client.port,
    )

    blockchain_services = list()
    for privkey in private_keys:
        blockchain = BlockChainService(
            privkey,
            registry_address,
            host,
            deploy_client.port,
        )
        blockchain_services.append(blockchain)

    return BlockchainServices(deploy_blockchain, blockchain_services)

def token_addresses(
        request,
        token_amount,
        number_of_tokens,
        blockchain_services,
        cached_genesis,
        register_tokens):

    if cached_genesis:
        token_addresses = [
            address_decoder(token_address)
            for token_address in cached_genesis['config']['tokenAddresses']
        ]
    else:
        token_addresses = _token_addresses(
            token_amount,
            number_of_tokens,
            blockchain_services.deploy_service,
            blockchain_services.blockchain_services,
            register_tokens
        )

    return token_addresses

def blockchain_services(
        request,
        deploy_key,
        private_keys,
        poll_timeout,
        blockchain_backend,  # This fixture is required because it will start
                             # the geth subprocesses
        blockchain_rpc_ports,
        blockchain_type,
        tester_blockgas_limit,
        cached_genesis):

    verbose = request.config.option.verbose

    if blockchain_type in ('geth',):

        registry_address = None
        if cached_genesis:
            registry_address = cached_genesis['config'].get('defaultRegistryAddress')

            if registry_address:
                registry_address = address_decoder(registry_address)

        return _jsonrpc_services(
            deploy_key,
            private_keys,
            verbose,
            poll_timeout,
            blockchain_rpc_ports[0],
            registry_address,
        )

    raise ValueError('unknown cluster type {}'.format(blockchain_type))



if __name__ == '__main__':
    # 程序入口
    run()