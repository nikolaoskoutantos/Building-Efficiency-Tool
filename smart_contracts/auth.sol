// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * Minimal RBAC with reverse lookup, no OZ imports.
 *
 * - Multiple owners (set of wallets)
 * - Owners can grant/revoke roles to wallets
 * - You can register roles so the contract can return "all roles of wallet"
 * - Off-chain can call hasRole(role, wallet) and rolesOf(wallet)
 */
contract RBACReverse {
    // ---- owners (set) ----
    mapping(address => bool) public isOwner;
    uint256 public ownerCount;

    // ---- roles storage ----
    mapping(bytes32 => mapping(address => bool)) private _hasRole;

    // ---- registry for reverse lookup ----
    bytes32[] private _knownRoles;
    mapping(bytes32 => bool) private _roleRegistered;

    // ---- events ----
    event OwnerAdded(address indexed account);
    event OwnerRemoved(address indexed account);

    event RoleRegistered(bytes32 indexed role);
    event RoleGranted(bytes32 indexed role, address indexed account, address indexed sender);
    event RoleRevoked(bytes32 indexed role, address indexed account, address indexed sender);

    modifier onlyOwner() {
        require(isOwner[msg.sender], "not owner");
        _;
    }

    constructor(address[] memory initialOwners, bytes32[] memory initialRoles) {
        require(initialOwners.length > 0, "no owners");
        for (uint256 i = 0; i < initialOwners.length; i++) {
            address o = initialOwners[i];
            require(o != address(0), "owner=0");
            if (!isOwner[o]) {
                isOwner[o] = true;
                ownerCount += 1;
                emit OwnerAdded(o);
            }
        }

        // register optional initial roles
        for (uint256 i = 0; i < initialRoles.length; i++) {
            _registerRole(initialRoles[i]);
        }
    }

    // ---------------- Owners ----------------
    function addOwner(address account) external onlyOwner {
        require(account != address(0), "account=0");
        if (!isOwner[account]) {
            isOwner[account] = true;
            ownerCount += 1;
            emit OwnerAdded(account);
        }
    }

    function removeOwner(address account) external onlyOwner {
        require(account != address(0), "account=0");
        require(isOwner[account], "not an owner");
        require(ownerCount > 1, "last owner");
        isOwner[account] = false;
        ownerCount -= 1;
        emit OwnerRemoved(account);
    }

    // ---------------- Roles API ----------------
    function registerRole(bytes32 role) external onlyOwner {
        _registerRole(role);
    }

    function getKnownRoles() external view returns (bytes32[] memory) {
        return _knownRoles;
    }

    function hasRole(bytes32 role, address account) external view returns (bool) {
        return _hasRole[role][account];
    }

    function grantRole(bytes32 role, address account) external onlyOwner {
        require(account != address(0), "account=0");
        require(_roleRegistered[role], "role not registered");
        if (!_hasRole[role][account]) {
            _hasRole[role][account] = true;
            emit RoleGranted(role, account, msg.sender);
        }
    }

    function revokeRole(bytes32 role, address account) external onlyOwner {
        require(account != address(0), "account=0");
        if (_hasRole[role][account]) {
            _hasRole[role][account] = false;
            emit RoleRevoked(role, account, msg.sender);
        }
    }

    // Reverse lookup: wallet -> roles[]
    function rolesOf(address account) external view returns (bytes32[] memory roles) {
        uint256 n = _knownRoles.length;

        uint256 count = 0;
        for (uint256 i = 0; i < n; i++) {
            bytes32 r = _knownRoles[i];
            if (_hasRole[r][account]) count++;
        }

        roles = new bytes32[](count);
        uint256 k = 0;
        for (uint256 i = 0; i < n; i++) {
            bytes32 r = _knownRoles[i];
            if (_hasRole[r][account]) roles[k++] = r;
        }
    }

    // ---------------- Internal ----------------
    function _registerRole(bytes32 role) internal {
        require(role != bytes32(0), "role=0");
        if (_roleRegistered[role]) return;
        _roleRegistered[role] = true;
        _knownRoles.push(role);
        emit RoleRegistered(role);
    }
}
