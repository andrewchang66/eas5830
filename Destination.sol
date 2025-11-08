// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "./BridgeToken.sol";

contract Destination is AccessControl {
    bytes32 public constant WARDEN_ROLE = keccak256("BRIDGE_WARDEN_ROLE");
    bytes32 public constant CREATOR_ROLE = keccak256("CREATOR_ROLE");
	mapping( address => address) public underlying_tokens;
	mapping( address => address) public wrapped_tokens;
	address[] public tokens;

	event Creation( address indexed underlying_token, address indexed wrapped_token );
	event Wrap( address indexed underlying_token, address indexed wrapped_token, address indexed to, uint256 amount );
	event Unwrap( address indexed underlying_token, address indexed wrapped_token, address frm, address indexed to, uint256 amount );

    constructor( address admin ) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(CREATOR_ROLE, admin);
        _grantRole(WARDEN_ROLE, admin);
    }

	function wrap(address _underlying_token, address _recipient, uint256 _amount ) public onlyRole(WARDEN_ROLE) {
		//YOUR CODE HERE
	    address _wrapped = wrapped[_underlying];
	    require(_wrapped != address(0), "token not registered");
	    require(_to != address(0), "bad recipient");
	    require(_amount > 0, "zero amount");
	
	    BridgeToken(_wrapped).mint(_to, _amount);
	    emit Wrap(_underlying, _to, _amount);
	}

	function unwrap(address _wrapped_token, address _recipient, uint256 _amount ) public {
		//YOUR CODE HERE
	    require(_wrappedToken != address(0), "bad wrapped token");
	    require(_recipientOnSource != address(0), "bad source recipient");
	    require(_amount > 0, "zero amount");
	
	    BridgeToken(_wrappedToken).burnFrom(msg.sender, _amount);
	
	    emit Unwrap(_wrappedToken, _recipientOnSource, _amount);
	}

	function createToken(address _underlying_token, string memory name, string memory symbol ) public onlyRole(CREATOR_ROLE) returns(address) {
		//YOUR CODE HERE
    	require(_underlying != address(0), "invalid underlying");
    	require(wrapped[_underlying] == address(0), "already created");

    	BridgeToken token = new BridgeToken(_name, _symbol);
    	address _wrapped = address(token);

    	wrapped[_underlying] = _wrapped;
    	emit Creation(_underlying, _wrapped);
    	return _wrapped;

	}

}


