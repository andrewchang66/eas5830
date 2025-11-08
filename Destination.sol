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
    address w = wrapped_tokens[_underlying_token];
    require(w != address(0), "token not registered");
    require(_recipient != address(0), "bad recipient");
    require(_amount > 0, "zero amount");

    BridgeToken(w).mint(_recipient, _amount);
    emit Wrap(_underlying_token, w, _recipient, _amount);
	}

	function unwrap(address _wrapped_token, address _recipient, uint256 _amount ) public {
		//YOUR CODE HERE
    require(_wrapped_token != address(0), "bad wrapped token");
    address u = underlying_tokens[_wrapped_token];
    require(u != address(0), "unknown wrapped token");
    require(_recipient != address(0), "bad source recipient");
    require(_amount > 0, "zero amount");

    // If your BridgeToken uses a different burn method (e.g., bridgeBurnFrom),
    // change the next line accordingly.
    BridgeToken(_wrapped_token).burnFrom(msg.sender, _amount);

    emit Unwrap(u, _wrapped_token, msg.sender, _recipient, _amount);
	}

	function createToken(address _underlying_token, string memory name, string memory symbol ) public onlyRole(CREATOR_ROLE) returns(address) {
    require(_underlying_token != address(0), "invalid underlying");
    require(wrapped_tokens[_underlying_token] == address(0), "already created");

    // BridgeToken constructor: (address _underlying, string memory name, string memory symbol, address admin)
    BridgeToken token = new BridgeToken(_underlying_token, name, symbol, address(this));
    address w = address(token);

    wrapped_tokens[_underlying_token] = w;
    underlying_tokens[w] = _underlying_token;
    tokens.push(w);

    emit Creation(_underlying_token, w);
    return w;
	}

}


