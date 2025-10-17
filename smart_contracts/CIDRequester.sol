// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@chainlink/contracts/src/v0.8/ChainlinkClient.sol";

// ---- OpenZeppelin (all from the same version to avoid Context conflicts) ----
import "https://raw.githubusercontent.com/OpenZeppelin/openzeppelin-contracts/v4.9.6/contracts/access/Ownable.sol";
import "https://raw.githubusercontent.com/OpenZeppelin/openzeppelin-contracts/v4.9.6/contracts/security/Pausable.sol";
import "https://raw.githubusercontent.com/OpenZeppelin/openzeppelin-contracts/v4.9.6/contracts/security/ReentrancyGuard.sol";


contract CIDRequester is ChainlinkClient, Ownable, Pausable, ReentrancyGuard {
    using Chainlink for Chainlink.Request;

    // ---- Chainlink config ----
    address public operator;     // Operator (oracle) contract
    bytes32 public jobId;        // Direct Request job ID
    uint256 public feeJuels;     // LINK (juels) paid by THIS contract to the oracle per request

    // ---- Billing (LINK) ----
    // If user has an active subscription with remaining > 0 → consume 1.
    // Else → charge on-demand: pull LINK from user via transferFrom before sending the oracle request.
    uint256 public onDemandPriceJuels; // LINK (juels) charged to the user per invocation when no subscription

    struct Tier {
        uint256 periodSec;            // e.g., 30 days in seconds
        uint256 priceJuels;           // LINK price to buy one period
        uint256 includedInvocations;  // included requests per period
        bool active;
    }
    mapping(uint8 => Tier) public tiers;

    struct Subscription {
        uint64 expiresAt; // unix time
        uint32 remaining; // invocations left
    }
    mapping(address => Subscription) public subs;

    // ---- Result storage (minimal) ----
    string public latestCID;
    bytes32 public latestRequestId;

    // ---- Events ----
    event Requested(bytes32 indexed requestId, address indexed user, string lat, string lon, string service);
    event Fulfilled(bytes32 indexed requestId, string cid);

    event OperatorUpdated(address indexed oldOp, address indexed newOp);
    event JobIdUpdated(bytes32 indexed oldJobId, bytes32 indexed newJobId);
    event FeeUpdated(uint256 oldFee, uint256 newFee);

    event OnDemandPriceUpdated(uint256 oldPrice, uint256 newPrice);
    event TierUpdated(uint8 indexed id, uint256 periodSec, uint256 priceJuels, uint256 includedInvocations, bool active);
    event Subscribed(address indexed user, uint8 indexed tierId, uint256 periodsPurchased, uint64 newExpiresAt, uint32 newRemaining);
    event ChargedOnDemand(address indexed user, uint256 amountJuels);

    constructor(
        address _linkToken,
        address _operator,
        bytes32 _jobId,
        uint256 _feeJuels
    ) {
        // Chainlink setup
        _setChainlinkToken(_linkToken);
        _setChainlinkOracle(_operator);
        operator = _operator;
        jobId = _jobId;
        feeJuels = _feeJuels;

        // Test-friendly default; admin can change later
        onDemandPriceJuels = 1e14; // 0.0001 LINK
    }

    // ---------- Admin ----------
    function pause() external onlyOwner { _pause(); }
    function unpause() external onlyOwner { _unpause(); }

    function setOperator(address _op) external onlyOwner {
        address old = operator;
        operator = _op;
        _setChainlinkOracle(_op);
        emit OperatorUpdated(old, _op);
    }

    function setJobId(bytes32 _jobId) external onlyOwner {
        bytes32 old = jobId;
        jobId = _jobId;
        emit JobIdUpdated(old, _jobId);
    }

    function setFeeJuels(uint256 _feeJuels) external onlyOwner {
        uint256 old = feeJuels;
        feeJuels = _feeJuels;
        emit FeeUpdated(old, _feeJuels);
    }

    function setOnDemandPriceJuels(uint256 _price) external onlyOwner {
        uint256 old = onDemandPriceJuels;
        onDemandPriceJuels = _price;
        emit OnDemandPriceUpdated(old, _price);
    }

    function setTier(
        uint8 id,
        uint256 periodSec,
        uint256 priceJuels,
        uint256 includedInvocations,
        bool active
    ) external onlyOwner {
        tiers[id] = Tier({
            periodSec: periodSec,
            priceJuels: priceJuels,
            includedInvocations: includedInvocations,
            active: active
        });
        emit TierUpdated(id, periodSec, priceJuels, includedInvocations, active);
    }

    // ---------- Subscriptions ----------
    /// @notice Buy or extend a subscription. Caller must approve LINK to this contract first.
    function subscribe(uint8 tierId, uint256 periods) external nonReentrant whenNotPaused {
        require(periods > 0, "periods=0");
        Tier memory t = tiers[tierId];
        require(t.active, "tier inactive");
        require(t.periodSec > 0 && t.includedInvocations > 0, "bad tier");

        uint256 cost = t.priceJuels * periods;
        LinkTokenInterface link = LinkTokenInterface(_chainlinkTokenAddress());
        require(link.transferFrom(msg.sender, address(this), cost), "LINK transferFrom failed");

        Subscription storage s = subs[msg.sender];
        uint64 nowTs = uint64(block.timestamp);
        uint64 base = s.expiresAt > nowTs ? s.expiresAt : nowTs;

        s.expiresAt = base + uint64(t.periodSec * periods);
        s.remaining += uint32(t.includedInvocations * periods);

        emit Subscribed(msg.sender, tierId, periods, s.expiresAt, s.remaining);
    }

    // ---------- Internal billing ----------
    function _consumeOrCharge(address user) internal {
        Subscription storage s = subs[user];
        if (s.expiresAt >= block.timestamp && s.remaining > 0) {
            // consume included invocation
            s.remaining -= 1;
        } else {
            // charge on-demand
            uint256 price = onDemandPriceJuels;
            require(price > 0, "on-demand disabled");
            LinkTokenInterface link = LinkTokenInterface(_chainlinkTokenAddress());
            require(link.transferFrom(user, address(this), price), "LINK on-demand transferFrom failed");
            emit ChargedOnDemand(user, price);
        }
    }

    // ---------- Request (single endpoint flow) ----------
    function requestCID(
        string calldata lat,
        string calldata lon,
        string calldata service
    ) external nonReentrant whenNotPaused returns (bytes32 reqId) {
        require(jobId != 0x0, "jobId not set");
        require(operator != address(0), "operator not set");

        // Ensure we can pay the oracle BEFORE billing the user
        LinkTokenInterface link = LinkTokenInterface(_chainlinkTokenAddress());
        require(link.balanceOf(address(this)) >= feeJuels, "Insufficient LINK in contract");

        // Bill the user (subscription consumes; otherwise on-demand charge)
        _consumeOrCharge(msg.sender);

        // Build and send Chainlink request
        Chainlink.Request memory req = _buildChainlinkRequest(
            jobId,
            address(this),
            this.fulfillBytes.selector
        );

        // EA expects: requestData (JSON string) and path="cid"
        string memory idStr = string(abi.encodePacked("req_", _uToStr(block.number)));
        string memory body = string(
            abi.encodePacked(
                "{\"id\":\"", idStr, "\",\"data\":{",
                    "\"service\":\"", service, "\",",
                    "\"lat\":\"", lat, "\",",
                    "\"lon\":\"", lon, "\"",
                "}}"
            )
        );

        Chainlink._add(req, "requestData", body);
        Chainlink._add(req, "path", "cid");

        reqId = _sendChainlinkRequestTo(operator, req, feeJuels);
        latestRequestId = reqId;
        emit Requested(reqId, msg.sender, lat, lon, service);
    }

    // Fulfillment (bytes must be memory)
    function fulfillBytes(bytes32 _requestId, bytes memory _data)
        external
        recordChainlinkFulfillment(_requestId)
    {
        string memory cid = abi.decode(_data, (string));
        latestCID = cid;
        emit Fulfilled(_requestId, cid);
    }

    // ---------- Views ----------
    function isActive(address user) external view returns (bool active, uint64 expiresAt, uint32 remaining) {
        Subscription memory s = subs[user];
        return (s.expiresAt >= block.timestamp && s.remaining > 0, s.expiresAt, s.remaining);
    }

    // ---------- Treasury ----------
    function withdrawLink(address to, uint256 amount) external onlyOwner {
        require(to != address(0), "to=0");
        LinkTokenInterface link = LinkTokenInterface(_chainlinkTokenAddress());
        require(link.balanceOf(address(this)) >= amount, "Insufficient LINK balance");
        require(link.transfer(to, amount), "LINK transfer failed");
    }

    // uint -> string helper
    function _uToStr(uint256 v) internal pure returns (string memory) {
        if (v == 0) return "0";
        uint256 j = v;
        uint256 l;
        while (j != 0) { l++; j /= 10; }
        bytes memory b = new bytes(l);
        uint256 k = l;
        while (v != 0) {
            k--;
            b[k] = bytes1(uint8(48 + v % 10));
            v /= 10;
        }
        return string(b);
    }

    receive() external payable {}
}
