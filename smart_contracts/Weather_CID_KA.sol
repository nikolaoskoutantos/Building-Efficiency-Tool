// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "https://raw.githubusercontent.com/smartcontractkit/chainlink/v1.5.0/contracts/src/v0.8/ChainlinkClient.sol";
import "https://raw.githubusercontent.com/smartcontractkit/chainlink/v1.5.0/contracts/src/v0.8/interfaces/LinkTokenInterface.sol";
import "https://raw.githubusercontent.com/OpenZeppelin/openzeppelin-contracts/v4.9.6/contracts/access/Ownable.sol";
import "https://raw.githubusercontent.com/OpenZeppelin/openzeppelin-contracts/v4.9.6/contracts/security/Pausable.sol";
import "https://raw.githubusercontent.com/OpenZeppelin/openzeppelin-contracts/v4.9.6/contracts/security/ReentrancyGuard.sol";

contract CIDRequester is ChainlinkClient, Ownable, Pausable, ReentrancyGuard {
    using Chainlink for Chainlink.Request;

    // ---- Service IDs ----
    uint8 public constant SERVICE_CURRENT = 1;
    uint8 public constant SERVICE_FORECAST = 2;
    uint8 public constant SERVICE_HISTORICAL = 3;

    // ---- Chainlink config per service ----
    struct ServiceConfig {
        address operator;
        bytes32 jobId;
        uint256 feeJuels;
        bool active;
    }

    mapping(uint8 => ServiceConfig) public services;

    // ---- Billing (LINK) ----
    // Shared across all weather services.
    uint256 public onDemandPriceJuels;

    struct Tier {
        uint256 periodSec;
        uint256 priceJuels;
        uint256 includedInvocations;
        bool active;
    }
    mapping(uint8 => Tier) public tiers;

    struct Subscription {
        uint64 expiresAt;
        uint32 remaining;
    }
    mapping(address => Subscription) public subs;

    // ---- Result storage (minimal) ----
    string public latestCID;
    bytes32 public latestRequestId;

    // ---- Events ----
    event ServiceUpdated(
        uint8 indexed serviceId,
        address indexed operator,
        bytes32 indexed jobId,
        uint256 feeJuels,
        bool active
    );
    event Requested(
        bytes32 indexed requestId,
        address indexed user,
        uint8 indexed serviceId,
        string buildingDID,
        string service
    );
    event HistoricalRequested(
        bytes32 indexed requestId,
        address indexed user,
        string buildingDID,
        string service,
        string startDate,
        string endDate
    );
    event Fulfilled(bytes32 indexed requestId, string cid);

    event OnDemandPriceUpdated(uint256 oldPrice, uint256 newPrice);
    event TierUpdated(uint8 indexed id, uint256 periodSec, uint256 priceJuels, uint256 includedInvocations, bool active);
    event Subscribed(address indexed user, uint8 indexed tierId, uint256 periodsPurchased, uint64 newExpiresAt, uint32 newRemaining);
    event ChargedOnDemand(address indexed user, uint256 amountJuels);

    constructor(address _linkToken) {
        setChainlinkToken(_linkToken);
        onDemandPriceJuels = 1e14; // 0.0001 LINK
    }

    // ---------- Admin ----------
    function pause() external onlyOwner { _pause(); }
    function unpause() external onlyOwner { _unpause(); }

    function setService(
        uint8 serviceId,
        address operator,
        bytes32 jobId,
        uint256 feeJuels,
        bool active
    ) external onlyOwner {
        _setService(serviceId, operator, jobId, feeJuels, active);
    }

    function setOnDemandPriceJuels(uint256 price) external onlyOwner {
        uint256 old = onDemandPriceJuels;
        onDemandPriceJuels = price;
        emit OnDemandPriceUpdated(old, price);
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

    function _setService(
        uint8 serviceId,
        address operator,
        bytes32 jobId,
        uint256 feeJuels,
        bool active
    ) internal {
        require(
            serviceId == SERVICE_CURRENT ||
            serviceId == SERVICE_FORECAST ||
            serviceId == SERVICE_HISTORICAL,
            "invalid service"
        );
        require(operator != address(0), "operator=0");
        require(jobId != 0x0, "jobId=0");

        services[serviceId] = ServiceConfig({
            operator: operator,
            jobId: jobId,
            feeJuels: feeJuels,
            active: active
        });

        emit ServiceUpdated(serviceId, operator, jobId, feeJuels, active);
    }

    // ---------- Subscriptions ----------
    function subscribe(uint8 tierId, uint256 periods) external nonReentrant whenNotPaused {
        require(periods > 0, "periods=0");
        Tier memory t = tiers[tierId];
        require(t.active, "tier inactive");
        require(t.periodSec > 0 && t.includedInvocations > 0, "bad tier");

        uint256 cost = t.priceJuels * periods;
        LinkTokenInterface link = LinkTokenInterface(chainlinkTokenAddress());
        require(link.transferFrom(msg.sender, address(this), cost), "LINK transferFrom failed");

        Subscription storage s = subs[msg.sender];
        uint64 nowTs = uint64(block.timestamp);
        uint64 base = s.expiresAt > nowTs ? s.expiresAt : nowTs;

        s.expiresAt = base + uint64(t.periodSec * periods);
        s.remaining += uint32(t.includedInvocations * periods);

        emit Subscribed(msg.sender, tierId, periods, s.expiresAt, s.remaining);
    }

    // ---------- Request entry points ----------
    function requestCurrentCID(
        string calldata buildingDID,
        string calldata service
    ) external nonReentrant whenNotPaused returns (bytes32 reqId) {
        _consumeOrCharge(msg.sender);
        string memory body = string(
            abi.encodePacked(
                "{\"id\":\"", _requestIdString(), "\",\"data\":{",
                    "\"service\":\"", service, "\",",
                    "\"buildingDID\":\"", buildingDID, "\"",
                "}}"
            )
        );

        reqId = _sendServiceRequest(SERVICE_CURRENT, body);
        emit Requested(reqId, msg.sender, SERVICE_CURRENT, buildingDID, service);
    }

    function requestForecastCID(
        string calldata buildingDID,
        string calldata service
    ) external nonReentrant whenNotPaused returns (bytes32 reqId) {
        _consumeOrCharge(msg.sender);
        string memory body = string(
            abi.encodePacked(
                "{\"id\":\"", _requestIdString(), "\",\"data\":{",
                    "\"service\":\"", service, "\",",
                    "\"buildingDID\":\"", buildingDID, "\"",
                "}}"
            )
        );

        reqId = _sendServiceRequest(SERVICE_FORECAST, body);
        emit Requested(reqId, msg.sender, SERVICE_FORECAST, buildingDID, service);
    }

    function requestHistoricalCID(
        string calldata buildingDID,
        string calldata service,
        string calldata startDate,
        string calldata endDate
    ) external nonReentrant whenNotPaused returns (bytes32 reqId) {
        _consumeOrCharge(msg.sender);
        string memory body = string(
            abi.encodePacked(
                "{\"id\":\"", _requestIdString(), "\",\"data\":{",
                    "\"service\":\"", service, "\",",
                    "\"buildingDID\":\"", buildingDID, "\",",
                    "\"start_date\":\"", startDate, "\",",
                    "\"end_date\":\"", endDate, "\"",
                "}}"
            )
        );

        reqId = _sendServiceRequest(SERVICE_HISTORICAL, body);
        emit HistoricalRequested(reqId, msg.sender, buildingDID, service, startDate, endDate);
    }

    // ---------- Internal billing ----------
    function _consumeOrCharge(address user) internal {
        Subscription storage s = subs[user];
        if (s.expiresAt >= block.timestamp && s.remaining > 0) {
            s.remaining -= 1;
        } else {
            uint256 price = onDemandPriceJuels;
            require(price > 0, "on-demand disabled");
            LinkTokenInterface link = LinkTokenInterface(chainlinkTokenAddress());
            require(link.transferFrom(user, address(this), price), "LINK on-demand transferFrom failed");
            emit ChargedOnDemand(user, price);
        }
    }

    function _sendServiceRequest(uint8 serviceId, string memory body) internal returns (bytes32 reqId) {
        ServiceConfig memory svc = services[serviceId];
        require(svc.active, "service inactive");
        require(svc.operator != address(0), "operator not set");
        require(svc.jobId != 0x0, "jobId not set");

        LinkTokenInterface link = LinkTokenInterface(chainlinkTokenAddress());
        require(link.balanceOf(address(this)) >= svc.feeJuels, "Insufficient LINK in contract");

        Chainlink.Request memory req = buildChainlinkRequest(
            svc.jobId,
            address(this),
            this.fulfillBytes.selector
        );

        Chainlink.add(req, "requestData", body);
        Chainlink.add(req, "path", "cid");

        reqId = sendChainlinkRequestTo(svc.operator, req, svc.feeJuels);
        latestRequestId = reqId;
    }

    function _requestIdString() internal view returns (string memory) {
        return string(
            abi.encodePacked(
                "req_",
                _uToStr(block.number),
                "_",
                _uToStr(block.timestamp)
            )
        );
    }

    // ---------- Fulfillment ----------
    function fulfillBytes(bytes32 requestId, bytes memory data)
        external
        recordChainlinkFulfillment(requestId)
    {
        string memory cid = abi.decode(data, (string));
        latestCID = cid;
        emit Fulfilled(requestId, cid);
    }

    // ---------- Views ----------
    function isActive(address user) external view returns (bool active, uint64 expiresAt, uint32 remaining) {
        Subscription memory s = subs[user];
        return (s.expiresAt >= block.timestamp && s.remaining > 0, s.expiresAt, s.remaining);
    }

    // ---------- Treasury ----------
    function withdrawLink(address to, uint256 amount) external onlyOwner {
        require(to != address(0), "to=0");
        LinkTokenInterface link = LinkTokenInterface(chainlinkTokenAddress());
        require(link.balanceOf(address(this)) >= amount, "Insufficient LINK balance");
        require(link.transfer(to, amount), "LINK transfer failed");
    }

    // ---------- Utils ----------
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
