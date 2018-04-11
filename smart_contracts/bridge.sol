pragma solidity ^0.4.15;


/// general helpers.
/// `internal` so they get compiled into contracts using them.
library Helpers {
    /// returns whether `array` contains `value`.
    function addressArrayContains(address[] array, address value) internal returns (bool) {
        for (uint256 i = 0; i < array.length; i++) {
            if (array[i] == value) {
                return true;
            }
        }
        return false;
    }

    // returns the digits of `inputValue` as a string.
    // example: `uintToString(12345678)` returns `"12345678"`
    function uintToString(uint256 inputValue) internal   returns (string) {
        // figure out the length of the resulting string
        uint256 length = 0;
        uint256 currentValue = inputValue;
        do {
            length++;
            currentValue /= 10;
        } while (currentValue != 0);
        // allocate enough memory
        bytes memory result = new bytes(length);
        // construct the string backwards
        uint256 i = length - 1;
        currentValue = inputValue;
        do {
            result[i--] = byte(48 + currentValue % 10);
            currentValue /= 10;
        } while (currentValue != 0);
        return string(result);
    }

    /// returns whether signatures (whose components are in `vs`, `rs`, `ss`)
    /// contain `requiredSignatures` distinct correct signatures
    /// where signer is in `allowed_signers`
    /// that signed `message`
    function hasEnoughValidSignatures(bytes message, uint8[] vs, bytes32[] rs, bytes32[] ss, address[] allowed_signers, uint256 requiredSignatures) internal   returns (bool) {
        // not enough signatures
        if (vs.length < requiredSignatures) {
            return false;
        }

        var hash = MessageSigning.hashMessage(message);
        var encountered_addresses = new address[](allowed_signers.length);

        for (uint256 i = 0; i < requiredSignatures; i++) {
            var recovered_address = ecrecover(hash, vs[i], rs[i], ss[i]);
            // only signatures by addresses in `addresses` are allowed
            if (!addressArrayContains(allowed_signers, recovered_address)) {
                return false;
            }
            // duplicate signatures are not allowed
            if (addressArrayContains(encountered_addresses, recovered_address)) {
                return false;
            }
            encountered_addresses[i] = recovered_address;
        }
        return true;
    }

}

// helpers for message signing.
// `internal` so they get compiled into contracts using them.
library MessageSigning {
    function recoverAddressFromSignedMessage(bytes signature, bytes message) internal   returns (address) {
        require(signature.length == 65);
        bytes32 r;
        bytes32 s;
        bytes1 v;
        // solium-disable-next-line security/no-inline-assembly
        assembly {
            r := mload(add(signature, 0x20))
            s := mload(add(signature, 0x40))
            v := mload(add(signature, 0x60))
        }
        return ecrecover(hashMessage(message), uint8(v), r, s);
    }

    function hashMessage(bytes message) internal   returns (bytes32) {
        bytes memory prefix = "\x19Ethereum Signed Message:\n";
        return keccak256(prefix, Helpers.uintToString(message.length), message);
    }
}

library Message {
    // layout of message :: bytes:
    // offset  0: 32 bytes :: uint256 (big endian) - message length (not part of message. any `bytes` begins with the length in memory)
    // offset 32: 20 bytes :: address - recipient address
    // offset 52: 32 bytes :: uint256 (big endian) - value
    // offset 84: 32 bytes :: bytes32 - transaction hash
    // offset 116: 32 bytes :: uint256 (big endian) - home gas price

    // mload always reads 32 bytes.
    // if mload reads an address it only interprets the last 20 bytes as the address.
    // so we can and have to start reading recipient at offset 20 instead of 32.
    // if we were to read at 32 the address would contain part of value and be corrupted.
    // when reading from offset 20 mload will ignore 12 bytes followed
    // by the 20 recipient address bytes and correctly convert it into an address.
    // this saves some storage/gas over the alternative solution
    // which is padding address to 32 bytes and reading recipient at offset 32.
    // for more details see discussion in:
    // https://github.com/paritytech/parity-bridge/issues/61

    function getRecipient(bytes message) internal   returns (address) {
        address recipient;
        // solium-disable-next-line security/no-inline-assembly
        assembly {
            recipient := mload(add(message, 20))
        }
        return recipient;
    }

    function getValue(bytes message) internal   returns (uint256) {
        uint256 value;
        // solium-disable-next-line security/no-inline-assembly
        assembly {
            value := mload(add(message, 52))
        }
        return value;
    }

    function getTransactionHash(bytes message) internal   returns (bytes32) {
        bytes32 hash;
        // solium-disable-next-line security/no-inline-assembly
        assembly {
            hash := mload(add(message, 84))
        }
        return hash;
    }

    function getHomeGasPrice(bytes message) internal   returns (uint256) {
        uint256 gasPrice;
        // solium-disable-next-line security/no-inline-assembly
        assembly {
            gasPrice := mload(add(message, 116))
        }
        return gasPrice;
    }
}


/// Library used only to test Message library via rpc calls
library MessageTest {
    function getRecipient(bytes message) public   returns (address) {
        return Message.getRecipient(message);
    }

    function getValue(bytes message) public   returns (uint256) {
        return Message.getValue(message);
    }

    function getTransactionHash(bytes message) public   returns (bytes32) {
        return Message.getTransactionHash(message);
    }

    function getHomeGasPrice(bytes message) public   returns (uint256) {
        return Message.getHomeGasPrice(message);
    }
}


contract HomeBridge {
    /// Number of authorities signatures required to withdraw the money.
    ///
    /// Must be lesser than number of authorities.
    uint256 public requiredSignatures;

    /// The gas cost of calling `HomeBridge.withdraw`.
    ///
    /// Is subtracted from `value` on withdraw.
    /// recipient pays the relaying authority for withdraw.
    /// this shuts down attacks that exhaust authorities funds on home chain.
    uint256 public estimatedGasCostOfWithdraw;

    /// reject deposits that would increase `this.balance` beyond this value.
    /// security feature:
    /// limits the total amount of home/mainnet ether that can be lost
    /// if the bridge is faulty or compromised in any way!
    /// set to 0 to disable.
    uint256 public maxTotalHomeContractBalance;

    /// reject deposits whose `msg.value` is higher than this value.
    /// security feature.
    /// set to 0 to disable.
    uint256 public maxSingleDepositValue;

    /// Contract authorities.
    address[] public authorities;

    /// Used foreign transaction hashes.
    mapping (bytes32 => bool) withdraws;

    /// Event created on money deposit.
    event Deposit (address recipient, uint256 value);

    /// Event created on money withdraw.
    event Withdraw (address recipient, uint256 value, bytes32 transactionHash);

    /// Constructor.
    function HomeBridge(
        uint256 requiredSignaturesParam,
        address[] authoritiesParam,
        uint256 estimatedGasCostOfWithdrawParam,
        uint256 maxTotalHomeContractBalanceParam,
        uint256 maxSingleDepositValueParam
    ) public
    {
        require(requiredSignaturesParam != 0);
        require(requiredSignaturesParam <= authoritiesParam.length);
        requiredSignatures = requiredSignaturesParam;
        authorities = authoritiesParam;
        estimatedGasCostOfWithdraw = estimatedGasCostOfWithdrawParam;
        maxTotalHomeContractBalance = maxTotalHomeContractBalanceParam;
        maxSingleDepositValue = maxSingleDepositValueParam;
    }

    /// Should be used to deposit money.
    function () public payable {
        require(maxSingleDepositValue == 0 || msg.value <= maxSingleDepositValue);
        // the value of `this.balance` in payable methods is increased
        // by `msg.value` before the body of the payable method executes
        require(maxTotalHomeContractBalance == 0 || this.balance <= maxTotalHomeContractBalance);
        Deposit(msg.sender, msg.value);
    }

    /// final step of a withdraw.
    /// checks that `requiredSignatures` `authorities` have signed of on the `message`.
    /// then transfers `value` to `recipient` (both extracted from `message`).
    /// see message library above for a breakdown of the `message` contents.
    /// `vs`, `rs`, `ss` are the components of the signatures.

    /// anyone can call this, provided they have the message and required signatures!
    /// only the `authorities` can create these signatures.
    /// `requiredSignatures` authorities can sign arbitrary `message`s
    /// transfering any ether `value` out of this contract to `recipient`.
    /// bridge users must trust a majority of `requiredSignatures` of the `authorities`.
    function withdraw(uint8[] vs, bytes32[] rs, bytes32[] ss, bytes message) public {
        require(message.length == 116);

        // check that at least `requiredSignatures` `authorities` have signed `message`
        require(Helpers.hasEnoughValidSignatures(message, vs, rs, ss, authorities, requiredSignatures));

        address recipient = Message.getRecipient(message);
        uint256 value = Message.getValue(message);
        bytes32 hash = Message.getTransactionHash(message);
        uint256 homeGasPrice = Message.getHomeGasPrice(message);

        // if the recipient calls `withdraw` they can choose the gas price freely.
        // if anyone else calls `withdraw` they have to use the gas price
        // `homeGasPrice` specified by the user initiating the withdraw.
        // this is a security mechanism designed to shut down
        // malicious senders setting extremely high gas prices
        // and effectively burning recipients withdrawn value.
        // see https://github.com/paritytech/parity-bridge/issues/112
        // for further explanation.
        require((recipient == msg.sender) || (tx.gasprice == homeGasPrice));

        // The following two statements guard against reentry into this function.
        // Duplicated withdraw or reentry.
        require(!withdraws[hash]);
        // Order of operations below is critical to avoid TheDAO-like re-entry bug
        withdraws[hash] = true;

        uint256 estimatedWeiCostOfWithdraw = estimatedGasCostOfWithdraw * homeGasPrice;

        // charge recipient for relay cost
        uint256 valueRemainingAfterSubtractingCost = value - estimatedWeiCostOfWithdraw;

        // pay out recipient
        recipient.transfer(valueRemainingAfterSubtractingCost);

        // refund relay cost to relaying authority
        msg.sender.transfer(estimatedWeiCostOfWithdraw);

        Withdraw(recipient, valueRemainingAfterSubtractingCost, hash);
    }
}


contract ForeignBridge {

    // following is the part of ForeignBridge that is
    // no longer part of ERC20 and is concerned with
    // with moving tokens from and to HomeBridge

    struct SignaturesCollection {
        /// Signed message.
        bytes message;
        /// Authorities who signed the message.
        address[] signed;
        /// Signatures
        bytes[] signatures;
    }

    uint256 public requiredSignatures;
    address[] public authorities;
    mapping (bytes32 => address[]) deposits;
    mapping (bytes32 => SignaturesCollection) signatures;

    /// triggered when an authority confirms a deposit
    event DepositConfirmation(address recipient, uint256 value, bytes32 transactionHash);
    event Deposit(address recipient, uint256 value, bytes32 transactionHash);
    event Withdraw(address recipient, uint256 value, uint256 homeGasPrice);
    event WithdrawSignatureSubmitted(bytes32 messageHash);
    event CollectedSignatures(address authorityResponsibleForRelay, bytes32 messageHash);

    function ForeignBridge(
        uint256 _requiredSignatures,
        address[] _authorities
    ) public
    {
        require(_requiredSignatures != 0);
        require(_requiredSignatures <= _authorities.length);
        requiredSignatures = _requiredSignatures;
        authorities = _authorities;
    }

    function addressArrayContains(address[] array, address value) internal returns (bool) {
        for (uint256 i = 0; i < array.length; i++) {
            if (array[i] == value) {
                return true;
            }
        }
        return false;
    }

    /// require that sender is an authority
    modifier onlyAuthority() {
        require(addressArrayContains(authorities, msg.sender));
        _;
    }


    /// Used to deposit money to the contract.
    ///
    /// deposit recipient (bytes20)
    /// deposit value (uint256)
    /// mainnet transaction hash (bytes32) // to avoid transaction duplication
    function deposit(address recipient, uint256 value, bytes32 transactionHash) public onlyAuthority() {
        // Protection from misbehaving authority
        var hash = keccak256(recipient, value, transactionHash);

        // don't allow authority to confirm deposit twice
        require(!addressArrayContains(deposits[hash], msg.sender));

        deposits[hash].push(msg.sender);

        // TODO: this may cause troubles if requiredSignatures len is changed
        if (deposits[hash].length != requiredSignatures) {
            DepositConfirmation(recipient, value, transactionHash);
            return;
        }
        recipient.transfer(value * (10**8));
        Deposit(recipient, value * (10**8), transactionHash);
    }

    /// Transfer `value` from `msg.sender`s local balance (on `foreign` chain) to `recipient` on `home` chain.
    ///
    /// immediately decreases `msg.sender`s local balance.
    /// emits a `Withdraw` event which will be picked up by the bridge authorities.
    /// bridge authorities will then sign off (by calling `submitSignature`) on a message containing `value`,
    /// `recipient` and the `hash` of the transaction on `foreign` containing the `Withdraw` event.
    /// once `requiredSignatures` are collected a `CollectedSignatures` event will be emitted.
    /// an authority will pick up `CollectedSignatures` an call `HomeBridge.withdraw`
    /// which transfers `value - relayCost` to `recipient` completing the transfer.
    function transferHomeViaRelay(address recipient, uint256 value) public {
        // require(balances[msg.sender] >= value);
        // don't allow 0 value transfers to home
        require(value > 0);

    }

    /// Should be used as sync tool
    ///
    /// Message is a message that should be relayed to main chain once authorities sign it.
    ///
    /// for withdraw message contains:
    /// withdrawal recipient (bytes20)
    /// withdrawal value (uint256)
    /// foreign transaction hash (bytes32) // to avoid transaction duplication
    function submitSignature(bytes signature, bytes message) public onlyAuthority() {
        // ensure that `signature` is really `message` signed by `msg.sender`
        require(msg.sender == MessageSigning.recoverAddressFromSignedMessage(signature, message));

        require(message.length == 116);
        var hash = keccak256(message);

        // each authority can only provide one signature per message
        require(!addressArrayContains(signatures[hash].signed, msg.sender));
        signatures[hash].message = message;
        signatures[hash].signed.push(msg.sender);
        signatures[hash].signatures.push(signature);

        // TODO: this may cause troubles if requiredSignatures len is changed
        if (signatures[hash].signed.length == requiredSignatures) {
            CollectedSignatures(msg.sender, hash);
        } else {
            WithdrawSignatureSubmitted(hash);
        }
    }

    /// Get signature
    function signature(bytes32 hash, uint256 index) public   returns (bytes) {
        return signatures[hash].signatures[index];
    }

    /// Get message
    function message(bytes32 hash) public   returns (bytes) {
        return signatures[hash].message;
    }
}
