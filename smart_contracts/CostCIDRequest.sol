// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Chainlink, ChainlinkClient} from "@chainlink/contracts/src/v0.8/operatorforwarder/ChainlinkClient.sol";
import {LinkTokenInterface} from "@chainlink/contracts/src/v0.8/interfaces/LinkTokenInterface.sol";

import "https://raw.githubusercontent.com/OpenZeppelin/openzeppelin-contracts/v4.9.6/contracts/access/Ownable.sol";
import "https://raw.githubusercontent.com/OpenZeppelin/openzeppelin-contracts/v4.9.6/contracts/security/Pausable.sol";
import "https://raw.githubusercontent.com/OpenZeppelin/openzeppelin-contracts/v4.9.6/contracts/security/ReentrancyGuard.sol";

contract CostsCIDRequester is ChainlinkClient, Ownable, Pausable, ReentrancyGuard {
    using Chainlink for Chainlink.Request;

    // -------- Chainlink config --------
    address public operator;        // Operator (oracle) contract
    bytes32 public jobId;           // DR job (bytes32 specId)
    uint256 public feeJuels;        // LINK paid per request (1 LINK = 1e18 juels)

    // -------- External Adapter control (body-only) --------
    // POST body will contain ONLY this job_id
    string private constant JOB_UUID = "5c1acaa7-7fe9-47b8-8c9d-e5be418e9cdc";

    // -------- Billing (subscription + on-demand) --------
    uint256 public onDemandPriceJuels; // LINK charged to caller when no active subscription

    struct Tier {
        uint256 periodSec;            // e.g., 30 days
        uint256 priceJuels;           // LINK per period (juels)
        uint256 includedInvocations;  // requests included per period
        bool    active;
    }
    mapping(uint8 => Tier) public tiers;

    struct Subscription {
        uint64 expiresAt; // unix time
        uint32 remaining; // remaining included requests
    }
    mapping(address => Subscription) public subs;

    // -------- Platform payout (owner-controlled) --------
    address public payoutWallet;     // platform share recipient
    uint16  public payoutBps;        // 100 = 1%, 10000 = 100%
    mapping(bytes32 => uint256) public pendingPayoutJuels; // scheduled platform share per requestId (on-demand only)

    // -------- Admin-defined rebate (cashback) --------
    // Only the owner can set the rebate recipient & percentage.
    address public rebateWallet;     // recipient of rebate (cashback)
    uint16  public rebateBps;        // rebate share in bps (default 8000 = 80%)
    mapping(bytes32 => uint256) public pendingRebateJuels; // scheduled rebate per requestId
    mapping(bytes32 => address) public rebateRecipient;     // capture recipient at schedule-time

    // -------- Results --------
    string  public latestCID;
    bytes32 public latestRequestId;

    // -------- Events --------
    event OperatorUpdated(address indexed oldOp, address indexed newOp);
    event JobIdUpdated(bytes32 indexed oldId, bytes32 indexed newId);
    event FeeUpdated(uint256 oldFee, uint256 newFee);
    event OnDemandPriceUpdated(uint256 oldPrice, uint256 newPrice);

    event TierUpdated(uint8 indexed id, uint256 periodSec, uint256 priceJuels, uint256 includedInvocations, bool active);
    event Subscribed(address indexed user, uint8 indexed tierId, uint256 periods, uint64 newExpiresAt, uint32 newRemaining);
    event ChargedOnDemand(address indexed user, uint256 amountJuels);

    event PayoutConfigUpdated(address wallet, uint16 bps);
    event PayoutScheduled(bytes32 indexed requestId, uint256 amountJuels);
    event PayoutSent(bytes32 indexed requestId, address to, uint256 amountJuels);
    event PayoutFailed(bytes32 indexed requestId, address to, uint256 amountJuels);

    event RebateConfigUpdated(address wallet, uint16 bps);
    event RebateScheduled(bytes32 indexed requestId, address indexed to, uint256 amountJuels);
    event RebateSent(bytes32 indexed requestId, address to, uint256 amountJuels);
    event RebateFailed(bytes32 indexed requestId, address to, uint256 amountJuels);

    event CostsRequested(bytes32 indexed requestId, address indexed user, string country);
    event CostsCIDFulfilled(bytes32 indexed requestId, string cid);

    constructor(
        address _linkToken,
        address _operator,
        bytes32 _jobId,
        uint256 _feeJuels
    ) {
        _setChainlinkToken(_linkToken);
        _setChainlinkOracle(_operator);
        operator = _operator;
        jobId    = _jobId;
        feeJuels = _feeJuels;

        onDemandPriceJuels = 1e14; // default: 0.0001 LINK (tune in prod)
        rebateBps          = 8000; // default: 80% rebate
    }

    // ---------------- Admin ----------------
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
        tiers[id] = Tier(periodSec, priceJuels, includedInvocations, active);
        emit TierUpdated(id, periodSec, priceJuels, includedInvocations, active);
    }

    // Platform payout config (global)
    function setPayoutConfig(address wallet, uint16 bps) external onlyOwner {
        require(wallet != address(0), "wallet=0");
        require(bps <= 10000, "bps>10000");
        // ensure combined distribution never exceeds 100%
        require(uint256(bps) + uint256(rebateBps) <= 10000, "payout+rebate>100%");
        payoutWallet = wallet;
        payoutBps = bps;
        emit PayoutConfigUpdated(wallet, bps);
    }

    // Rebate config (admin-only)
    function setRebateConfig(address wallet, uint16 bps) external onlyOwner {
        require(wallet != address(0) || bps == 0, "rebate wallet=0");
        require(bps <= 10000, "bps>10000");
        require(uint256(payoutBps) + uint256(bps) <= 10000, "payout+rebate>100%");
        rebateWallet = wallet;
        rebateBps = bps;
        emit RebateConfigUpdated(wallet, bps);
    }

    // ---------------- Subscriptions ----------------
    /// Caller must approve LINK to this contract first.
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

    // ---------------- Internal billing ----------------
    /// Returns how much was charged on-demand (0 if a subscription covered it).
    function _consumeOrCharge(address user) internal returns (uint256 chargedJuels) {
        Subscription storage s = subs[user];
        if (s.expiresAt >= block.timestamp && s.remaining > 0) {
            s.remaining -= 1;
            return 0;
        } else {
            uint256 price = onDemandPriceJuels;
            require(price > 0, "on-demand disabled");
            LinkTokenInterface link = LinkTokenInterface(_chainlinkTokenAddress());
            require(link.transferFrom(user, address(this), price), "LINK transferFrom failed");
            emit ChargedOnDemand(user, price);
            return price;
        }
    }

    // ---------------- Request (CID-only) ----------------
    /// EA must return JSON with key "cid".
    /// Keep `country` in ABI/event but DO NOT pass it to the EA body.
    function requestCostsCID(
        string calldata country
    ) external nonReentrant whenNotPaused returns (bytes32 reqId) {
        require(jobId != 0x0, "jobId not set");
        require(operator != address(0), "operator not set");

        // ensure we can pay oracle fee
        LinkTokenInterface link = LinkTokenInterface(_chainlinkTokenAddress());
        require(link.balanceOf(address(this)) >= feeJuels, "Insufficient LINK");

        // bill caller (sub or on-demand)
        uint256 charged = _consumeOrCharge(msg.sender);

        // build request
        Chainlink.Request memory req = _buildChainlinkRequest(
            jobId,
            address(this),
            this.fulfillCostsCID.selector
        );

        // ONLY job_id in the body
        string memory body = string(abi.encodePacked("{\"job_id\":\"", JOB_UUID, "\"}"));
        Chainlink._add(req, "requestData", body);
        Chainlink._add(req, "path", "cid");

        reqId = _sendChainlinkRequestTo(operator, req, feeJuels);
        latestRequestId = reqId;
        emit CostsRequested(reqId, msg.sender, country);

        // schedule platform share (only for on-demand payments)
        if (charged > 0 && payoutWallet != address(0) && payoutBps > 0) {
            uint256 share = (charged * payoutBps) / 10000;
            pendingPayoutJuels[reqId] = share;
            emit PayoutScheduled(reqId, share);
        }

        // schedule rebate (admin-defined; only for on-demand payments)
        if (charged > 0 && rebateWallet != address(0) && rebateBps > 0) {
            uint256 rebate = (charged * rebateBps) / 10000;
            pendingRebateJuels[reqId] = rebate;
            rebateRecipient[reqId] = rebateWallet; // lock recipient at schedule-time
            emit RebateScheduled(reqId, rebateWallet, rebate);
        }
    }

    // Fulfillment (string CID packed as bytes)
    function fulfillCostsCID(bytes32 _requestId, bytes memory _data)
        external
        recordChainlinkFulfillment(_requestId)
    {
        string memory cid = abi.decode(_data, (string));
        latestCID = cid;
        emit CostsCIDFulfilled(_requestId, cid);

        LinkTokenInterface link = LinkTokenInterface(_chainlinkTokenAddress());

        // try to send platform share; don't revert to avoid blocking oracle fulfill
        uint256 share = pendingPayoutJuels[_requestId];
        if (share > 0) {
            delete pendingPayoutJuels[_requestId];
            if (link.transfer(payoutWallet, share)) {
                emit PayoutSent(_requestId, payoutWallet, share);
            } else {
                pendingPayoutJuels[_requestId] = share;
                emit PayoutFailed(_requestId, payoutWallet, share);
            }
        }

        // try to send admin-defined rebate
        uint256 rebate = pendingRebateJuels[_requestId];
        address to = rebateRecipient[_requestId];
        if (rebate > 0 && to != address(0)) {
            delete pendingRebateJuels[_requestId];
            delete rebateRecipient[_requestId];
            if (link.transfer(to, rebate)) {
                emit RebateSent(_requestId, to, rebate);
            } else {
                pendingRebateJuels[_requestId] = rebate;
                rebateRecipient[_requestId] = to;
                emit RebateFailed(_requestId, to, rebate);
            }
        }
    }

    // ---------------- Views ----------------
    function isActive(address user) external view returns (bool active, uint64 expiresAt, uint32 remaining) {
        Subscription memory s = subs[user];
        return (s.expiresAt >= block.timestamp && s.remaining > 0, s.expiresAt, s.remaining);
    }

    // ---------------- Treasury ----------------
    function withdrawLink(address to, uint256 amount) external onlyOwner {
        require(to != address(0), "to=0");
        LinkTokenInterface link = LinkTokenInterface(_chainlinkTokenAddress());
        require(link.transfer(to, amount), "LINK transfer failed");
    }

    // ---------------- Utils ----------------
    function _uToStr(uint256 v) internal pure returns (string memory) {
        if (v == 0) return "0";
        uint256 j = v; uint256 l;
        while (j != 0) { l++; j /= 10; }
        bytes memory b = new bytes(l);
        uint256 k = l;
        while (v != 0) { k--; b[k] = bytes1(uint8(48 + v % 10)); v /= 10; }
        return string(b);
    }

    receive() external payable {}
}
