/*
This Token Contract implements the standard token functionality (https://github.com/ethereum/EIPs/issues/20), the ERC223 functionality (https://github.com/ethereum/EIPs/issues/223) as well as the following OPTIONAL extras intended for use by humans.

In other words. This is intended for deployment in something like a Token Factory or Mist wallet, and then used by humans.
Imagine coins, currencies, shares, voting weight, etc.
Machine-based, rapid creation of many tokens would not necessarily need these extra features or will be minted in other manners.

1) Initial Finite Supply (upon creation one specifies how much is minted).
2) In the absence of a token registry: Optional Decimal, Symbol & Name.

.*/

import "./ERC223Token.sol";

pragma solidity ^0.4.14;

contract userToken is ERC223Token {

    function userToken (
        address _user,
        uint256 _initialAmount,
        string _tokenName,
        uint8 _decimalUnits,
        string _tokenSymbol
        )
        ERC223Token(_initialAmount,_tokenName,_decimalUnits,_tokenSymbol)
        public
    {
        owner = _user;
    }
}
