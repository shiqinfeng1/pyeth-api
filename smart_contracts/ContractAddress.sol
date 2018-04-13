pragma solidity ^0.4.4;

contract ContractAddress {
    address public owner;
    address public atm_token;
    address public home_bridge;
    address public foreigin_bridge;

    modifier restricted() {
        if (msg.sender == owner) _;
    }

    function ContractAddress() public {
        owner = msg.sender;
    }
    
    function changeOwner(address _newOwner) restricted public {
        owner = _newOwner;
    }

    function set_atm_token(address new_address) restricted public {
        atm_token = new_address;
    }
    function set_home_bridge(address new_address) restricted public {
        home_bridge = new_address;
    }
    function set_foreigin_bridge(address new_address) restricted public {
        foreigin_bridge = new_address;
    }
}