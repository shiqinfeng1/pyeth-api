import "./ATMToken.sol";

pragma solidity ^0.4.14;

contract HomeBridge {
    /// Number of authorities signatures required to withdraw the money.
    ///
    /// Must be lesser than number of authorities.
    uint256 public requiredSignatures;
    address[] public authorities;

    /// Used foreign transaction hashes.
    mapping (bytes32 => address[]) withdraws;
    event WithdrawConfirmation(address recipient, uint256 value, bytes32 transactionHash);
    event Withdraw(address recipient, uint256 value, bytes32 transactionHash);

        /// require that sender is an authority
    modifier onlyAuthority() {
        require(addressArrayContains(authorities, msg.sender));
        _;
    }
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
    function addressArrayContains(address[] array, address value) internal returns (bool) {
        for (uint256 i = 0; i < array.length; i++) {
            if (array[i] == value) {
                return true;
            }
        }
        return false;
    }
    function withdraw(address token_address, address recipient, uint256 value, bytes32 transactionHash) public onlyAuthority(){
        
        ATMToken token = ATMToken(token_address);
        require(token.balanceOf(address(this)) > value);
        
        // Protection from misbehaving authority
        bytes32 hash = keccak256(recipient, value, transactionHash);

        // don't allow authority to confirm deposit twice
        if (addressArrayContains(withdraws[hash], msg.sender) == true){
            return;
        }

        withdraws[hash].push(msg.sender);

        // TODO: this may cause troubles if requiredSignatures len is changed
        if (withdraws[hash].length != requiredSignatures) {
            WithdrawConfirmation(recipient, value, transactionHash);
            return;
        }

        token.transfer(recipient,value);
        Withdraw(recipient, value, transactionHash);
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
    event TransferBack(address recipient, uint256 value);
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
    function deposit(address recipient, uint256 value, bytes32 transactionHash) payable public onlyAuthority() {
        
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
        TransferBack(msg.sender,value);
    }
}
