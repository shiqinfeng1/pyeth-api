

class Filter(object):
    def __init__(self, jsonrpc_client, filter_id_raw):
        self.filter_id_raw = filter_id_raw
        self.client = jsonrpc_client

    def _query_filter(self, function):
        filter_changes = self.client.call(function, self.filter_id_raw)

        # geth could return None
        if filter_changes is None:
            return []

        result = list()
        for log_event in filter_changes:
            address = address_decoder(log_event['address'])
            data = data_decoder(log_event['data'])
            topics = [
                decode_topic(topic)
                for topic in log_event['topics']
            ]

            result.append({
                'topics': topics,
                'data': data,
                'address': address,
            })

        return result

    def changes(self):
        return self._query_filter('eth_getFilterChanges')

    def getall(self):
        return self._query_filter('eth_getFilterLogs')

    def uninstall(self):
        self.client.call(
            'eth_uninstallFilter',
            self.filter_id_raw,
        )

def new_filter(jsonrpc_client, contract_address, topics, from_block=None, to_block=None):
    """ Custom new filter implementation to handle bad encoding from geth rpc. """
    if isinstance(from_block, int):
        from_block = hex(from_block)
    if isinstance(to_block, int):
        to_block = hex(to_block)
    json_data = {
        'fromBlock': from_block if from_block is not None else 'latest',
        'toBlock': to_block if to_block is not None else 'latest',
        'address': address_encoder(normalize_address(contract_address)),
    }

    if topics is not None:
        json_data['topics'] = [
            topic_encoder(topic)
            for topic in topics
        ]

    return jsonrpc_client.call('eth_newFilter', json_data)

class BlockchainEvents(object):
    """ Pyethapp events polling. """

    def get_contract_events_blocking(
            filters,
            condition=None,
            wait=constant.DEFAULT_RETRY_INTERVAL, timeout=constant.DEFAULT_TIMEOUT):
        """ Query the blockchain for all events of the smart contract at
        `contract_address` that match the filters `topics`, `from_block`, and
        `to_block`.
        """
        # Note: Issue #452 (https://github.com/raiden-network/raiden/issues/452)
        # tracks a suggested TODO, which will reduce the 3 RPC calls here to only
        # one using `eth_getLogs`. It will require changes in all testing frameworks
        # to be implemented though.

        events = filters.changes()
        for i in range(0, timeout + wait, wait):
            matching_logs = [event for event in events if not condition or condition(event)]
            if matching_logs:
                filters.uninstall()
                return matching_logs[0]
            elif i < timeout:
                gevent.sleep(wait)
        filters.uninstall()
        return None





