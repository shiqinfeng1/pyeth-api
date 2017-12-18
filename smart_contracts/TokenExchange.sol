pragma solidity ^0.4.11;

import "./ERC223Token.sol";
import "./Owned.sol";
import "./ContractReceiver.sol";

/// @title Raiden MicroTransfer Channels Contract.
contract TokenExchange is Owned,ContractReceiver{

    /*
     *  Data structures
     */

    address public owner;
    address public token_address;
    Token token;

    mapping (address => uint) userLockTokenAmount;

    event LogLockToken(
        address indexed _user,
        uint256 _amount);
    event LogSettleToken(
        address indexed _user,
        uint256 _amount);

    function TokenExchange(address _token) {
        require(_token != 0x0);

        owner = msg.sender;
        token_address = _token;
        token = ERC223Token(_token);
    }

    function lockToken(address _user, uint _amount) internal {
        require(_user != 0x0);
        require (msg.sender == owner || msg.sender == token_address);

        userLockTokenAmount[_user] += _amount;
        //fire event
        LogLockToken(_user,_amount);
    }  
    function settleToken(address _user, uint _amount) onlyOwner public {
        require(_user != 0x0);
        require(_amount > 0);

        token.transfer(_user,_amount);
        //fire event
        LogSettleToken(_user,_amount);
    }

    function tokenFallback(address _from, uint256 _value, bytes _data) public {
        require (msg.sender == owner || msg.sender == token_address);
        lockToken(_from, _value);
    }
}