pragma solidity ^0.4.15;

contract Owned {
    /// @dev `owner` is the only address that can call a function with this
    /// modifier
    modifier onlyOwner() {
        require(msg.sender == owner) ;
        _;
    }

    address public owner;

    /// @notice The Constructor assigns the message sender to be `owner`
    function Owned() public {
        owner = msg.sender;
    }

    address public newOwner;

    /// @notice `owner` can step down and assign some other address to this role
    /// @param _newOwner The address of the new owner. 0x0 can be used to create
    ///  an unowned neutral vault, however that cannot be undone
    function changeOwner(address _newOwner) public onlyOwner {
        newOwner = _newOwner;
    }

    function acceptOwnership() public {
        if (msg.sender == newOwner) {
            owner = newOwner;
        }
    }
}


contract TwitterAccount is  Owned {

    event Log_lotus(bytes32 _id, bytes32[] users);
    event Log_bind_account(bytes32 _id, address _addr);
    event Log_unbind_account(bytes32 _id);
    event Log_lotus_result(bytes32 _id, bytes32[] luckyboys,address[] luckyboys_addr);
    
    mapping(bytes32 => address) public accounts; //用户绑定的地址列表
    mapping(bytes32 => bytes32[]) public retweeters; //保存retweet_id对应的转发用户列表
    /*
    luckyboys_num: 中奖用户数目
    retweet_id: 推文id
    users_list:  所有转发的用户id 
    */
    function lotus(uint luckyboys_num, bytes32 retweet_id, bytes32[] users_list) public onlyOwner {
        
        bytes32[] memory valid_users_list = new bytes32[](users_list.length); //转发的用户id中,已绑定地址的用户
        address[] memory users_addr = new address[](users_list.length); //转发的用户id中,已绑定地址的用户的以太坊地址
        bytes32[] memory luckyboys = new bytes32[](luckyboys_num);  //中奖用户id
        address[] memory luckyboys_addr = new address[](luckyboys_num); //中奖用户地址
        
        retweeters[retweet_id] = users_list; //记录该推文在当前时间点被哪些用户转发
        
        Log_lotus(retweet_id,users_list);
        uint total_users = 0;
        //从所有转发的用户中,过滤已绑定地址的用户,并记录他们的绑定地址
        for(uint i=0;i<users_list.length;i++){
            if(accounts[users_list[i]]!=0){
                users_addr[total_users] = accounts[users_list[i]];
                valid_users_list[total_users] = users_list[i];
                total_users = total_users+1;
            }
        }
        
        //随机抽取中奖用户
        for(uint j=0;j<luckyboys_num;j++){
            //addmod(a,b,c) 取模算法: (a+b)%c
            uint temp = uint(block.blockhash(block.number-j-1))%total_users;//addmod(uint(block.blockhash(block.number-j-1)),0,total_users);
            luckyboys_addr[j] = users_addr[temp];
            luckyboys[j] = valid_users_list[temp]; 
        }
        
        Log_lotus_result(retweet_id,luckyboys,luckyboys_addr);
    }
    function bind_account(bytes32 _id, address _addr) public onlyOwner {
        accounts[_id] = _addr;
        Log_bind_account( _id,  _addr);
    }
     function unbind_account(bytes32 _id) public onlyOwner {
        delete accounts[_id];
        Log_unbind_account( _id);
    }
}