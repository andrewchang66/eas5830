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
		address wrapped = wrappedOf[underlying];
    require(wrapped != address(0), "token not registered"); // must be created first
    require(to != address(0), "bad recipient");
    require(amount > 0, "zero amount");

    // Mint wrapped tokens to recipient
    IBridgeToken(wrapped).mint(to, amount);
    emit Wrap(underlying, to, amount);
	}

	function unwrap(address _wrapped_token, address _recipient, uint256 _amount ) public {
		//YOUR CODE HERE
		require(wrappedToken != address(0), "bad wrapped token");
    require(recipientOnSource != address(0), "bad source recipient");
    require(amount > 0, "zero amount");

    // User must own enough wrapped tokens on destination
    require(IBridgeToken(wrappedToken).balanceOf(msg.sender) >= amount, "insufficient balance");

    // Burn user's wrapped tokens; Destination (this contract) is authorized to burn
    IBridgeToken(wrappedToken).burnFrom(msg.sender, amount);

    // Emit event so the relayer can call withdraw on source side to send real tokens to recipientOnSource
    emit Unwrap(wrappedToken, recipientOnSource, amount);
	}

	function createToken(address _underlying_token, string memory name, string memory symbol ) public onlyRole(CREATOR_ROLE) returns(address) {
		//YOUR CODE HERE
		require(underlying != address(0), "invalid underlying");
    require(wrappedOf[underlying] == address(0), "already created");

    // Deploy the wrapped token.
    BridgeToken token = new BridgeToken(name, symbol, underlying);
    wrapped = address(token);

    // Record mapping and emit event
    wrappedOf[underlying] = wrapped;
    emit Creation(underlying, wrapped);

    return wrapped;
	}

}


