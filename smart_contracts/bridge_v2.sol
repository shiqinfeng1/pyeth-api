pragma solidity ^0.4.14;

/*
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

*/
contract HomeBridge {
    /// Number of authorities signatures required to withdraw the money.
    ///
    /// Must be lesser than number of authorities.
    uint256 public requiredSignatures;
    address[] public authorities;

    /// Used foreign transaction hashes.
    mapping (bytes32 => bool) withdraws;

    /// Constructor.
    function HomeBridge(
        uint256 requiredSignaturesParam,
        address[] authoritiesParam
    ) public
    {
        require(requiredSignaturesParam != 0);
        require(requiredSignaturesParam <= authoritiesParam.length);
        requiredSignatures = requiredSignaturesParam;
        authorities = authoritiesParam;
    }
    function withdraw(address recipient, uint256 value, bytes32 transactionHash){

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
    event Transfer(address recipient, uint256 value);
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
        
        require(address(this).balance > value);
        
        // Protection from misbehaving authority
        bytes32 hash = keccak256(recipient, value, transactionHash);

        // don't allow authority to confirm deposit twice
        if (addressArrayContains(deposits[hash], msg.sender) == true){
            return;
        }

        deposits[hash].push(msg.sender);

        // TODO: this may cause troubles if requiredSignatures len is changed
        if (deposits[hash].length != requiredSignatures) {
            DepositConfirmation(recipient, value, transactionHash);
            return;
        }

        recipient.transfer(value);
        Deposit(recipient, value, transactionHash);
    }

    function () public payable {
        require(msg.value > 10**10);
        uint value = msg.value / 10**10;
        Transfer(msg.sender,value);
    }
}
