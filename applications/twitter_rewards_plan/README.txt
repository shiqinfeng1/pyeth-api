# usage

```
//连接一个以太坊节点:
app_twitter.chain.new_blockchain_proxy('eth','192.168.1.100:8545') //连接私链
//或者
app_twitter.chain.new_blockchain_proxy('eth','kovan') //通过infura连接第三方节点

//选择操作账户, 要求该账户在指定的keystore目录内
app_twitter.switch_sender('0x4fa07e11d6170b56afecb85f20028ea6687ddd62')

//部署twitter相关的合约, 保存部署成功的合约地址
app_twitter.deploy_twitter_rewards_contract('eth')

//查看官方账户ATMChainDev的消息列表
app_twitter.twitter_status_list()

//找到对应的待奖励的消息id, 并查看所有转发该消息的用户列表
app_twitter.retwitter_list(949087894802595840)

//根据注册的用户, 绑定他们的以太坊账户地址
//参数含义: 节点代理名字,用户id,用户以太坊地址,twitter合约地址(可选)
app_twitter.bind_account('eth','933373333063659520','0x63f1de588c7ce855b66cf24b595a8991f9211301','e95613337686d431fa0e6d46cd68fb4f0606142d')
app_twitter.bind_account('eth','895821883433549824','0x63f1de588c7ce855b66cf24b595a8991f9211302','e95613337686d431fa0e6d46cd68fb4f0606142d')
app_twitter.bind_account('eth','898096264822218752','0x63f1de588c7ce855b66cf24b595a8991f9211303','e95613337686d431fa0e6d46cd68fb4f0606142d')
app_twitter.bind_account('eth','875910354','0x63f1de588c7ce855b66cf24b595a8991f9211304','e95613337686d431fa0e6d46cd68fb4f0606142d')
app_twitter.bind_account('eth','708855853','0x63f1de588c7ce855b66cf24b595a8991f9211305','e95613337686d431fa0e6d46cd68fb4f0606142d')

//抽奖
//参数含义: 节点代理名字, 消息id, 中奖人数, twitter合约地址(可选)
app_twitter.get_luckyboys('eth','949087894802595840',3,'e95613337686d431fa0e6d46cd68fb4f0606142d')
```
