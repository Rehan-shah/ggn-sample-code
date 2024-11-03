// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract FederatedLearningPayment {

    address public owner;
    mapping(address => bool) public registeredClients;

    event PaymentIssued(address client, uint256 amount);

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Not contract owner");
        _;
    }

    function registerClient(address _client) public onlyOwner {
        registeredClients[_client] = true;
    }

    function issuePayment(address _client, uint256 _amount) public onlyOwner {
        require(registeredClients[_client], "Client not registered");
        emit PaymentIssued(_client, _amount);
    }
}
