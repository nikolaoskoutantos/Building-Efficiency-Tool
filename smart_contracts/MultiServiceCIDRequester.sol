// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "https://raw.githubusercontent.com/smartcontractkit/chainlink/v1.5.0/contracts/src/v0.8/ChainlinkClient.sol";
import "https://raw.githubusercontent.com/smartcontractkit/chainlink/v1.5.0/contracts/src/v0.8/interfaces/LinkTokenInterface.sol";
import "https://raw.githubusercontent.com/OpenZeppelin/openzeppelin-contracts/v4.9.6/contracts/access/Ownable.sol";
import "https://raw.githubusercontent.com/OpenZeppelin/openzeppelin-contracts/v4.9.6/contracts/security/Pausable.sol";
import "https://raw.githubusercontent.com/OpenZeppelin/openzeppelin-contracts/v4.9.6/contracts/security/ReentrancyGuard.sol";

contract MultiServiceCIDRequester is ChainlinkClient, Ownable, Pausable, ReentrancyGuard {
    using Chainlink for Chainlink.Request;

    uint8 public constant INPUT_STRING = 0;
    uint8 public constant INPUT_NUMBER = 1;
    uint8 public constant INPUT_BOOL = 2;

    uint8 public constant MODE_GENERIC = 0;
    uint8 public constant MODE_LAT_LON = 1;
    uint8 public constant MODE_BUILDING_DID = 2;
    uint8 public constant MODE_BUILDING_DID_DATE_RANGE = 3;

    uint8 public constant CALLBACK_ENVELOPE = 0;
    uint8 public constant CALLBACK_CID_ONLY = 1;
    uint8 public constant CALLBACK_CID_WITH_DEK = 2;
    uint8 public constant FULFILLMENT_DIRECT = 3;

    uint8 public constant STATUS_UNSET = 0;
    uint8 public constant STATUS_OK = 1;
    uint8 public constant STATUS_PARTIAL = 2;
    uint8 public constant STATUS_ERROR = 3;

    uint8 public constant LOCATOR_NONE = 0;
    uint8 public constant LOCATOR_IPFS = 1;
    uint8 public constant LOCATOR_HTTPS = 2;
    uint8 public constant LOCATOR_S3 = 3;
    uint8 public constant LOCATOR_ARWEAVE = 4;
    uint8 public constant LOCATOR_CUSTOM = 5;
    uint16 public constant BPS_DENOMINATOR = 10_000;
    uint64 public constant ABSOLUTE_MIN_PRICE_DELAY = 1 hours;

    struct ServiceConfig {
        address operator;
        address payoutWallet;
        bytes32 jobId;
        uint256 feeJuels;
        uint256 onDemandPriceJuels;
        uint64 requestExpirySec;
        uint16 providerShareBps;
        uint8 mode;
        uint8 callbackMode;
        bool active;
        bool frozen;
        string name;
        string description;
        string responsePath;
        string[] inputKeys;
        string[] inputDescriptions;
        uint8[] inputKinds;
    }

    struct Tier {
        uint256 periodSec;
        uint256 priceJuels;
        uint32 includedInvocations;
        bool active;
    }

    struct Subscription {
        uint64 expiresAt;
        uint32 remaining;
        uint8 tierId;
    }

    struct RequestRecord {
        address requester;
        uint256 chargedJuels;
        uint64 requestedAt;
        uint64 directFulfillBy;
        uint32 serviceId;
        uint8 tierIdUsed;
        bool subscriptionUsed;
    }

    struct ResponseEnvelope {
        bytes32 contentHash;
        uint64 fulfilledAt;
        uint8 status;
        uint8 locatorType;
        bool encrypted;
        bool fulfilled;
        bool hasWrappedDEK;
        bool hasRawData;
        string locator;
        string mimeType;
        string schemaRef;
        bytes wrappedDEK;
        bytes rawData;
        string note;
    }

    struct PendingPricing {
        uint256 feeJuels;
        uint256 onDemandPriceJuels;
        uint64 executeAfter;
        bool exists;
    }

    mapping(uint32 => ServiceConfig) private services;
    mapping(uint32 => bool) public serviceExists;
    mapping(uint32 => bool) private serviceIndexed;
    uint32[] private serviceIds;

    mapping(uint32 => mapping(uint8 => Tier)) private tiersByService;
    mapping(address => mapping(uint32 => Subscription)) public subs;

    mapping(bytes32 => RequestRecord) private requests;
    mapping(bytes32 => ResponseEnvelope) private responses;
    mapping(bytes32 => address) public authorizedFulfiller;
    mapping(address => bytes32[]) private userRequests;
    mapping(address => uint256) public providerLinkBalance;
    mapping(uint32 => PendingPricing) public pendingPricing;
    uint256 public totalProviderOwed;
    uint64 public minPriceChangeDelay;

    mapping(bytes32 => string) public requestLocator;
    bytes32 public latestRequestId;

    event ServiceUpserted(
        uint32 indexed serviceId,
        string name,
        bytes32 indexed jobId,
        uint8 mode,
        uint8 callbackMode,
        bool active
    );
    event ServicePayoutWalletUpdated(uint32 indexed serviceId, address indexed payoutWallet);
    event ServiceRevenueShareUpdated(uint32 indexed serviceId, uint16 providerShareBps);
    event ServicePricingChangeScheduled(
        uint32 indexed serviceId,
        uint256 feeJuels,
        uint256 onDemandPriceJuels,
        uint64 executeAfter
    );
    event ServicePricingUpdated(
        uint32 indexed serviceId,
        uint256 feeJuels,
        uint256 onDemandPriceJuels
    );
    event MinPriceChangeDelayUpdated(uint64 oldDelay, uint64 newDelay);
    event ServiceActivationUpdated(uint32 indexed serviceId, bool active);
    event ServiceFrozen(uint32 indexed serviceId);
    event TierUpdated(
        uint32 indexed serviceId,
        uint8 indexed tierId,
        uint256 periodSec,
        uint256 priceJuels,
        uint32 includedInvocations,
        bool active
    );
    event Subscribed(
        address indexed user,
        uint32 indexed serviceId,
        uint8 indexed tierId,
        uint256 periods,
        uint64 expiresAt,
        uint32 remaining
    );
    event ChargedOnDemand(address indexed user, uint32 indexed serviceId, uint256 amountJuels);
    event ProviderCredited(uint32 indexed serviceId, address indexed payoutWallet, uint256 amountJuels);
    event ProviderWithdrawn(address indexed payoutWallet, uint256 amountJuels);
    event RequestCancelled(bytes32 indexed requestId, address indexed requester, uint32 indexed serviceId);
    event ETHWithdrawn(address indexed to, uint256 amount);
    event RequestRefunded(bytes32 indexed requestId, address indexed requester, uint256 amountJuels);
    event Requested(
        bytes32 indexed requestId,
        address indexed user,
        uint32 indexed serviceId,
        string provider,
        bool subscriptionUsed,
        uint8 tierIdUsed,
        uint256 chargedJuels
    );
    event Fulfilled(
        bytes32 indexed requestId,
        address indexed user,
        uint32 indexed serviceId,
        uint8 status,
        uint8 locatorType,
        string locator,
        bool encrypted,
        bool hasWrappedDEK,
        bool hasRawData
    );

    constructor(address _linkToken) {
        setChainlinkToken(_linkToken);
        minPriceChangeDelay = 1 hours;
    }

    function pause() external onlyOwner { _pause(); }
    function unpause() external onlyOwner { _unpause(); }

    function cancelRequest(
        bytes32 requestId,
        uint256 payment,
        bytes4 callbackFunctionId,
        uint256 expiration
    ) external onlyOwner {
        RequestRecord storage rec = requests[requestId];
        require(rec.requester != address(0), "unknown request");
        require(!responses[requestId].fulfilled, "already fulfilled");

        if (rec.subscriptionUsed) {
            subs[rec.requester][rec.serviceId].remaining += 1;
        }

        if (services[rec.serviceId].callbackMode != FULFILLMENT_DIRECT) {
            cancelChainlinkRequest(requestId, payment, callbackFunctionId, expiration);
        }

        delete authorizedFulfiller[requestId];
        emit RequestCancelled(requestId, rec.requester, rec.serviceId);
    }

    function claimExpiredRefund(bytes32 requestId) external nonReentrant {
        RequestRecord storage rec = requests[requestId];
        require(rec.requester == msg.sender, "not requester");
        require(!responses[requestId].fulfilled, "already fulfilled");
        require(
            services[rec.serviceId].callbackMode == FULFILLMENT_DIRECT,
            "not direct request"
        );
        require(
            rec.directFulfillBy > 0 && block.timestamp > rec.directFulfillBy,
            "not expired"
        );

        // Restore subscription invocation regardless of payment type
        if (rec.subscriptionUsed) {
            subs[msg.sender][rec.serviceId].remaining += 1;
        }

        uint256 refundAmount = rec.chargedJuels;
        rec.chargedJuels = 0;
        delete authorizedFulfiller[requestId];

        // Only transfer LINK if user paid on-demand
        if (refundAmount > 0) {
            uint256 providerAmount = (refundAmount * services[rec.serviceId].providerShareBps) / BPS_DENOMINATOR;
            if (providerAmount > 0 && providerLinkBalance[services[rec.serviceId].payoutWallet] >= providerAmount) {
                providerLinkBalance[services[rec.serviceId].payoutWallet] -= providerAmount;
                totalProviderOwed -= providerAmount;
            }
            LinkTokenInterface link = LinkTokenInterface(chainlinkTokenAddress());
            require(link.transfer(msg.sender, refundAmount), "LINK refund failed");
            emit RequestRefunded(requestId, msg.sender, refundAmount);
        }
    }

    function withdrawETH(address payable to, uint256 amount) external onlyOwner {
        require(to != address(0), "to=0");
        (bool ok, ) = to.call{value: amount}("");
        require(ok, "ETH transfer failed");
        emit ETHWithdrawn(to, amount);
    }

    function upsertService(
        uint32 serviceId,
        address operator,
        address payoutWallet,
        bytes32 jobId,
        uint256 feeJuels,
        uint256 onDemandPriceJuels,
        uint64 requestExpirySec,
        uint16 providerShareBps,
        uint8 mode,
        uint8 callbackMode,
        string calldata name,
        string calldata description,
        string calldata responsePath,
        string[] calldata inputKeys,
        string[] calldata inputDescriptions,
        uint8[] calldata inputKinds,
        bool active
    ) external onlyOwner {
        require(serviceId != 0, "serviceId=0");
        require(operator != address(0), "operator=0");
        require(payoutWallet != address(0), "payout=0");
        if (callbackMode != FULFILLMENT_DIRECT) {
            require(jobId != 0x0, "jobId=0");
        }
        require(providerShareBps <= BPS_DENOMINATOR, "bad bps");
        require(mode <= MODE_BUILDING_DID_DATE_RANGE, "bad mode");
        require(callbackMode <= FULFILLMENT_DIRECT, "bad callback");
        if (callbackMode != FULFILLMENT_DIRECT) {
            require(onDemandPriceJuels >= feeJuels, "onDemand < fee");
        }
        require(inputKeys.length == inputDescriptions.length, "schema mismatch");
        require(inputKeys.length == inputKinds.length, "type mismatch");

        ServiceConfig storage svc = services[serviceId];
        require(!svc.frozen, "service frozen");

        for (uint256 i = 0; i < inputKinds.length; i++) {
            require(inputKinds[i] <= INPUT_BOOL, "bad input kind");
        }

        svc.operator = operator;
        svc.payoutWallet = payoutWallet;
        svc.jobId = jobId;
        svc.feeJuels = feeJuels;
        svc.onDemandPriceJuels = onDemandPriceJuels;
        svc.requestExpirySec = requestExpirySec;
        svc.providerShareBps = providerShareBps;
        svc.mode = mode;
        svc.callbackMode = callbackMode;
        svc.active = active;
        svc.name = name;
        svc.description = description;
        svc.responsePath = responsePath;

        delete svc.inputKeys;
        delete svc.inputDescriptions;
        delete svc.inputKinds;

        for (uint256 i = 0; i < inputKeys.length; i++) {
            svc.inputKeys.push(inputKeys[i]);
            svc.inputDescriptions.push(inputDescriptions[i]);
            svc.inputKinds.push(inputKinds[i]);
        }

        serviceExists[serviceId] = true;
        if (!serviceIndexed[serviceId]) {
            serviceIndexed[serviceId] = true;
            serviceIds.push(serviceId);
        }

        emit ServiceUpserted(serviceId, name, jobId, mode, callbackMode, active);
        emit ServicePayoutWalletUpdated(serviceId, payoutWallet);
        emit ServiceRevenueShareUpdated(serviceId, providerShareBps);
    }

    function freezeService(uint32 serviceId) external onlyOwner {
        require(serviceExists[serviceId], "unknown service");
        services[serviceId].frozen = true;
        emit ServiceFrozen(serviceId);
    }

    function setServicePricing(
        uint32 serviceId,
        uint256 feeJuels,
        uint256 onDemandPriceJuels
    ) external onlyOwner {
        require(serviceExists[serviceId], "unknown service");
        pendingPricing[serviceId] = PendingPricing({
            feeJuels: feeJuels,
            onDemandPriceJuels: onDemandPriceJuels,
            executeAfter: uint64(block.timestamp) + minPriceChangeDelay,
            exists: true
        });
        emit ServicePricingChangeScheduled(
            serviceId,
            feeJuels,
            onDemandPriceJuels,
            pendingPricing[serviceId].executeAfter
        );
    }

    function executeServicePricing(uint32 serviceId) external onlyOwner {
        PendingPricing memory pending = pendingPricing[serviceId];
        require(pending.exists, "no pending pricing");
        require(block.timestamp >= pending.executeAfter, "pricing timelocked");

        ServiceConfig storage svc = services[serviceId];
        if (svc.callbackMode != FULFILLMENT_DIRECT) {
            require(pending.onDemandPriceJuels >= pending.feeJuels, "onDemand < fee");
        }

        svc.feeJuels = pending.feeJuels;
        svc.onDemandPriceJuels = pending.onDemandPriceJuels;
        delete pendingPricing[serviceId];
        emit ServicePricingUpdated(serviceId, pending.feeJuels, pending.onDemandPriceJuels);
    }

    function setMinPriceChangeDelay(uint64 newDelay) external onlyOwner {
        require(newDelay >= ABSOLUTE_MIN_PRICE_DELAY, "delay too short");
        uint64 oldDelay = minPriceChangeDelay;
        minPriceChangeDelay = newDelay;
        emit MinPriceChangeDelayUpdated(oldDelay, newDelay);
    }

    function _safeToUint32(uint256 value) internal pure returns (uint32) {
        require(value <= type(uint32).max, "overflow uint32");
        return uint32(value);
    }

    function _safeToUint64(uint256 value) internal pure returns (uint64) {
        require(value <= type(uint64).max, "overflow uint64");
        return uint64(value);
    }

    function setServiceActive(uint32 serviceId, bool active) external onlyOwner {
        require(serviceExists[serviceId], "unknown service");
        services[serviceId].active = active;
        emit ServiceActivationUpdated(serviceId, active);
    }

    function setServicePayoutWallet(uint32 serviceId, address payoutWallet) external onlyOwner {
        require(serviceExists[serviceId], "unknown service");
        require(payoutWallet != address(0), "payout=0");
        services[serviceId].payoutWallet = payoutWallet;
        emit ServicePayoutWalletUpdated(serviceId, payoutWallet);
    }

    function setServiceRevenueShare(uint32 serviceId, uint16 providerShareBps) external onlyOwner {
        require(serviceExists[serviceId], "unknown service");
        require(providerShareBps <= BPS_DENOMINATOR, "bad bps");
        services[serviceId].providerShareBps = providerShareBps;
        emit ServiceRevenueShareUpdated(serviceId, providerShareBps);
    }

    function setServiceRequestExpiry(uint32 serviceId, uint64 requestExpirySec) external onlyOwner {
        require(serviceExists[serviceId], "unknown service");
        services[serviceId].requestExpirySec = requestExpirySec;
    }

    function setTier(
        uint32 serviceId,
        uint8 tierId,
        uint256 periodSec,
        uint256 priceJuels,
        uint32 includedInvocations,
        bool active
    ) external onlyOwner {
        require(serviceExists[serviceId], "unknown service");
        tiersByService[serviceId][tierId] = Tier({
            periodSec: periodSec,
            priceJuels: priceJuels,
            includedInvocations: includedInvocations,
            active: active
        });

        emit TierUpdated(serviceId, tierId, periodSec, priceJuels, includedInvocations, active);
    }

    function subscribe(
        uint32 serviceId,
        uint8 tierId,
        uint256 periods
    ) external nonReentrant whenNotPaused {
        require(periods > 0, "periods=0");
        require(serviceExists[serviceId], "unknown service");
        require(services[serviceId].active, "service inactive");

        Tier memory t = tiersByService[serviceId][tierId];
        require(t.active, "tier inactive");
        require(t.periodSec > 0 && t.includedInvocations > 0, "bad tier");

        uint256 cost = t.priceJuels * periods;
        LinkTokenInterface link = LinkTokenInterface(chainlinkTokenAddress());
        require(link.transferFrom(msg.sender, address(this), cost), "LINK transferFrom failed");
        _creditProvider(serviceId, cost);

        Subscription storage s = subs[msg.sender][serviceId];
        uint64 nowTs = uint64(block.timestamp);
        uint64 base = s.expiresAt > nowTs ? s.expiresAt : nowTs;

        s.expiresAt = _safeToUint64(uint256(base) + t.periodSec * periods);
        s.remaining = _safeToUint32(uint256(s.remaining) + uint256(t.includedInvocations) * periods);
        s.tierId = tierId;

        emit Subscribed(msg.sender, serviceId, tierId, periods, s.expiresAt, s.remaining);
    }

    function requestService(
        uint32 serviceId,
        string calldata provider,
        string[] calldata values
    ) external nonReentrant whenNotPaused returns (bytes32 reqId) {
        reqId = _requestService(serviceId, provider, values);
    }

    function requestCID(
        uint32 serviceId,
        string calldata lat,
        string calldata lon,
        string calldata provider
    ) external nonReentrant whenNotPaused returns (bytes32 reqId) {
        require(serviceExists[serviceId], "unknown service");
        require(services[serviceId].mode == MODE_LAT_LON, "wrong mode");

        string[] memory values = new string[](2);
        values[0] = lat;
        values[1] = lon;
        reqId = _requestService(serviceId, provider, values);
    }

    function requestCurrentCID(
        uint32 serviceId,
        string calldata buildingDID,
        string calldata provider
    ) external nonReentrant whenNotPaused returns (bytes32 reqId) {
        require(serviceExists[serviceId], "unknown service");
        require(services[serviceId].mode == MODE_BUILDING_DID, "wrong mode");

        string[] memory values = new string[](2);
        values[0] = buildingDID;
        values[1] = "current";
        reqId = _requestService(serviceId, provider, values);
    }

    function requestForecastCID(
        uint32 serviceId,
        string calldata buildingDID,
        string calldata provider
    ) external nonReentrant whenNotPaused returns (bytes32 reqId) {
        require(serviceExists[serviceId], "unknown service");
        require(services[serviceId].mode == MODE_BUILDING_DID, "wrong mode");

        string[] memory values = new string[](2);
        values[0] = buildingDID;
        values[1] = "forecast";
        reqId = _requestService(serviceId, provider, values);
    }

    function requestHistoricalCID(
        uint32 serviceId,
        string calldata buildingDID,
        string calldata provider,
        string calldata startDate,
        string calldata endDate
    ) external nonReentrant whenNotPaused returns (bytes32 reqId) {
        require(serviceExists[serviceId], "unknown service");
        require(services[serviceId].mode == MODE_BUILDING_DID_DATE_RANGE, "wrong mode");

        string[] memory values = new string[](3);
        values[0] = buildingDID;
        values[1] = startDate;
        values[2] = endDate;
        reqId = _requestService(serviceId, provider, values);
    }

    function _requestService(
        uint32 serviceId,
        string memory provider,
        string[] memory values
    ) internal returns (bytes32 reqId) {
        require(serviceExists[serviceId], "unknown service");
        ServiceConfig storage svc = services[serviceId];
        require(svc.active, "service inactive");
        require(svc.operator != address(0), "operator not set");

        _validateRequestValues(svc, values);

        (uint256 chargedJuels, uint8 tierIdUsed, bool subscriptionUsed) = _consumeOrCharge(serviceId, msg.sender);

        if (svc.callbackMode == FULFILLMENT_DIRECT) {
            reqId = _directRequestId(serviceId, msg.sender, provider, values);
        } else {
            require(svc.jobId != 0x0, "jobId not set");
            LinkTokenInterface link = LinkTokenInterface(chainlinkTokenAddress());
            require(link.balanceOf(address(this)) >= svc.feeJuels, "Insufficient LINK in contract");

            Chainlink.Request memory req = buildChainlinkRequest(
                svc.jobId,
                address(this),
                _callbackSelectorFor(svc.callbackMode)
            );

            bytes memory requestData = _buildEncodedRequestData(serviceId, msg.sender, provider, values);
            req.addBytes("requestData", requestData);
            if (bytes(svc.responsePath).length > 0) {
                Chainlink.add(req, "path", svc.responsePath);
            }

            reqId = sendChainlinkRequestTo(svc.operator, req, svc.feeJuels);
        }
        latestRequestId = reqId;
        authorizedFulfiller[reqId] = svc.operator;

        requests[reqId] = RequestRecord({
            requester: msg.sender,
            chargedJuels: chargedJuels,
            requestedAt: uint64(block.timestamp),
            directFulfillBy: svc.callbackMode == FULFILLMENT_DIRECT && svc.requestExpirySec > 0
                ? uint64(block.timestamp) + svc.requestExpirySec
                : 0,
            serviceId: serviceId,
            tierIdUsed: tierIdUsed,
            subscriptionUsed: subscriptionUsed
        });
        userRequests[msg.sender].push(reqId);

        emit Requested(reqId, msg.sender, serviceId, provider, subscriptionUsed, tierIdUsed, chargedJuels);
    }

    function _consumeOrCharge(
        uint32 serviceId,
        address user
    ) internal returns (uint256 chargedJuels, uint8 tierIdUsed, bool subscriptionUsed) {
        Subscription storage s = subs[user][serviceId];
        if (s.expiresAt >= block.timestamp && s.remaining > 0) {
            s.remaining -= 1;
            tierIdUsed = s.tierId;
            subscriptionUsed = true;
            chargedJuels = 0;
        } else {
            uint256 price = services[serviceId].onDemandPriceJuels;
            require(price > 0, "on-demand disabled");
            LinkTokenInterface link = LinkTokenInterface(chainlinkTokenAddress());
            require(link.transferFrom(user, address(this), price), "LINK on-demand transferFrom failed");
            _creditProvider(serviceId, price);
            emit ChargedOnDemand(user, serviceId, price);
            chargedJuels = price;
            tierIdUsed = 0;
            subscriptionUsed = false;
        }
    }

    function _creditProvider(uint32 serviceId, uint256 amount) internal {
        if (amount == 0) return;
        ServiceConfig storage svc = services[serviceId];
        uint256 providerAmount = (amount * svc.providerShareBps) / BPS_DENOMINATOR;
        if (providerAmount == 0) return;

        address payoutWallet = svc.payoutWallet;
        require(payoutWallet != address(0), "payout=0");
        providerLinkBalance[payoutWallet] += providerAmount;
        totalProviderOwed += providerAmount;
        emit ProviderCredited(serviceId, payoutWallet, providerAmount);
    }

    function _callbackSelectorFor(uint8 callbackMode) internal pure returns (bytes4 selector) {
        if (callbackMode == CALLBACK_CID_ONLY) {
            return this.fulfillCIDOnly.selector;
        }
        if (callbackMode == CALLBACK_CID_WITH_DEK) {
            return this.fulfillCIDWithDEK.selector;
        }
        return this.fulfillResponse.selector;
    }

    function _directRequestId(
        uint32 serviceId,
        address requester,
        string memory provider,
        string[] memory values
    ) internal view returns (bytes32 reqId) {
        return keccak256(
            abi.encode(
                address(this),
                block.chainid,
                serviceId,
                requester,
                provider,
                values,
                block.number,
                block.timestamp,
                userRequests[requester].length
            )
        );
    }

    function _validateRequestValues(
        ServiceConfig storage svc,
        string[] memory values
    ) internal view {
        require(values.length == svc.inputKeys.length, "bad input count");
        for (uint256 i = 0; i < values.length; i++) {
            _validateInputValue(values[i], svc.inputKinds[i]);
        }
    }

    function _validateInputValue(string memory value, uint8 kind) internal pure {
        if (kind == INPUT_STRING) return;

        bytes memory raw = bytes(value);
        require(raw.length > 0, "empty literal");

        if (kind == INPUT_BOOL) {
            bool isTrue = keccak256(raw) == keccak256(bytes("true"));
            bool isFalse = keccak256(raw) == keccak256(bytes("false"));
            require(isTrue || isFalse, "bad bool");
            return;
        }

        bool hasDigit = false;
        bool hasDot = false;
        for (uint256 i = 0; i < raw.length; i++) {
            bytes1 c = raw[i];
            bool isDigit = c >= 0x30 && c <= 0x39;
            bool isSign = (i == 0 && (c == 0x2d || c == 0x2b));
            bool isDot = c == 0x2e;
            require(isDigit || isSign || isDot, "bad number");
            if (isDot) {
                require(!hasDot, "bad number");
                hasDot = true;
            }
            if (isDigit) hasDigit = true;
        }
        require(hasDigit, "bad number");
    }

    function _buildEncodedRequestData(
        uint32 serviceId,
        address requester,
        string memory provider,
        string[] memory values
    ) internal pure returns (bytes memory) {
        return abi.encode(serviceId, requester, provider, values);
    }

    function fulfillResponse(bytes32 requestId, bytes memory data)
        external
        recordChainlinkFulfillment(requestId)
    {
        (
            uint8 status,
            uint8 locatorType,
            bool encrypted,
            string memory locator,
            string memory mimeType,
            string memory schemaRef,
            bytes32 contentHash,
            bytes memory wrappedDEK,
            bytes memory rawData,
            string memory note
        ) = abi.decode(data, (uint8, uint8, bool, string, string, string, bytes32, bytes, bytes, string));

        _storeFulfillment(
            requestId,
            status,
            locatorType,
            encrypted,
            locator,
            mimeType,
            schemaRef,
            contentHash,
            wrappedDEK,
            rawData,
            note
        );
    }

    function fulfillCIDOnly(bytes32 requestId, bytes memory data)
        external
        recordChainlinkFulfillment(requestId)
    {
        string memory cid = abi.decode(data, (string));
        _storeFulfillment(
            requestId,
            STATUS_OK,
            LOCATOR_IPFS,
            false,
            cid,
            "",
            "",
            bytes32(0),
            bytes(""),
            bytes(""),
            ""
        );
    }

    function fulfillCIDWithDEK(bytes32 requestId, bytes memory data)
        external
        recordChainlinkFulfillment(requestId)
    {
        (string memory cid, bytes memory wrappedDEK) = abi.decode(data, (string, bytes));
        _storeFulfillment(
            requestId,
            STATUS_OK,
            LOCATOR_IPFS,
            wrappedDEK.length > 0,
            cid,
            "",
            "",
            bytes32(0),
            wrappedDEK,
            bytes(""),
            ""
        );
    }

    function fulfillDirect(bytes32 requestId, bytes calldata data) external {
        require(msg.sender == authorizedFulfiller[requestId], "unauthorized fulfiller");
        RequestRecord storage requestMeta = requests[requestId];
        require(requestMeta.requester != address(0), "unknown request");
        require(
            services[requestMeta.serviceId].callbackMode == FULFILLMENT_DIRECT,
            "not direct request"
        );
        require(
            requestMeta.directFulfillBy == 0 || block.timestamp <= requestMeta.directFulfillBy,
            "request expired"
        );
        (
            uint8 status,
            uint8 locatorType,
            bool encrypted,
            string memory locator,
            string memory mimeType,
            string memory schemaRef,
            bytes32 contentHash,
            bytes memory wrappedDEK,
            bytes memory rawData,
            string memory note
        ) = abi.decode(data, (uint8, uint8, bool, string, string, string, bytes32, bytes, bytes, string));

        _storeFulfillment(
            requestId,
            status,
            locatorType,
            encrypted,
            locator,
            mimeType,
            schemaRef,
            contentHash,
            wrappedDEK,
            rawData,
            note
        );
    }

    function _storeFulfillment(
        bytes32 requestId,
        uint8 status,
        uint8 locatorType,
        bool encrypted,
        string memory locator,
        string memory mimeType,
        string memory schemaRef,
        bytes32 contentHash,
        bytes memory wrappedDEK,
        bytes memory rawData,
        string memory note
    ) internal {
        require(status <= STATUS_ERROR, "bad status");
        require(locatorType <= LOCATOR_CUSTOM, "bad locator");
        require(!responses[requestId].fulfilled, "already fulfilled");

        ResponseEnvelope storage r = responses[requestId];
        r.status = status;
        r.locatorType = locatorType;
        r.encrypted = encrypted;
        r.fulfilledAt = uint64(block.timestamp);
        if (bytes(locator).length > 0) {
            r.locator = locator;
        } else {
            delete r.locator;
        }
        if (bytes(mimeType).length > 0) {
            r.mimeType = mimeType;
        } else {
            delete r.mimeType;
        }
        if (bytes(schemaRef).length > 0) {
            r.schemaRef = schemaRef;
        } else {
            delete r.schemaRef;
        }
        r.contentHash = contentHash;
        if (bytes(note).length > 0) {
            r.note = note;
        } else {
            delete r.note;
        }
        r.fulfilled = true;
        r.hasWrappedDEK = wrappedDEK.length > 0;
        r.hasRawData = rawData.length > 0;
        if (wrappedDEK.length > 0) {
            r.wrappedDEK = wrappedDEK;
        } else {
            delete r.wrappedDEK;
        }
        if (rawData.length > 0) {
            r.rawData = rawData;
        } else {
            delete r.rawData;
        }

        requestLocator[requestId] = locator;
        delete authorizedFulfiller[requestId];

        RequestRecord storage requestMeta = requests[requestId];
        emit Fulfilled(
            requestId,
            requestMeta.requester,
            requestMeta.serviceId,
            status,
            locatorType,
            locator,
            encrypted,
            r.hasWrappedDEK,
            r.hasRawData
        );
    }

    function getService(
        uint32 serviceId
    ) external view returns (
        address operator,
        address payoutWallet,
        bytes32 jobId,
        uint256 feeJuels,
        uint256 onDemandPriceJuels,
        uint64 requestExpirySec,
        uint16 providerShareBps,
        uint8 mode,
        uint8 callbackMode,
        bool active,
        bool frozen,
        string memory name,
        string memory description,
        string memory responsePath
    ) {
        require(serviceExists[serviceId], "unknown service");
        ServiceConfig storage svc = services[serviceId];
        return (
            svc.operator,
            svc.payoutWallet,
            svc.jobId,
            svc.feeJuels,
            svc.onDemandPriceJuels,
            svc.requestExpirySec,
            svc.providerShareBps,
            svc.mode,
            svc.callbackMode,
            svc.active,
            svc.frozen,
            svc.name,
            svc.description,
            svc.responsePath
        );
    }

    function getServiceInputSchema(
        uint32 serviceId
    ) external view returns (
        string[] memory inputKeys,
        string[] memory inputDescriptions,
        uint8[] memory inputKinds
    ) {
        require(serviceExists[serviceId], "unknown service");
        ServiceConfig storage svc = services[serviceId];
        return (svc.inputKeys, svc.inputDescriptions, svc.inputKinds);
    }

    function getServiceIds() external view returns (uint32[] memory ids) {
        return serviceIds;
    }

    function getTier(
        uint32 serviceId,
        uint8 tierId
    ) external view returns (
        uint256 periodSec,
        uint256 priceJuels,
        uint32 includedInvocations,
        bool active
    ) {
        Tier storage t = tiersByService[serviceId][tierId];
        return (t.periodSec, t.priceJuels, t.includedInvocations, t.active);
    }

    function isActive(
        address user,
        uint32 serviceId
    ) external view returns (bool active, uint64 expiresAt, uint32 remaining, uint8 tierId) {
        Subscription memory s = subs[user][serviceId];
        return (s.expiresAt >= block.timestamp && s.remaining > 0, s.expiresAt, s.remaining, s.tierId);
    }

    function getRequest(
        bytes32 requestId
    ) external view returns (
        address requester,
        uint256 chargedJuels,
        uint64 requestedAt,
        uint64 directFulfillBy,
        uint32 serviceId,
        uint8 tierIdUsed,
        bool subscriptionUsed
    ) {
        RequestRecord storage r = requests[requestId];
        return (
            r.requester,
            r.chargedJuels,
            r.requestedAt,
            r.directFulfillBy,
            r.serviceId,
            r.tierIdUsed,
            r.subscriptionUsed
        );
    }

    function getResponse(
        bytes32 requestId
    ) external view returns (
        uint8 status,
        uint8 locatorType,
        bool encrypted,
        string memory locator,
        string memory mimeType,
        string memory schemaRef,
        bytes32 contentHash,
        uint64 fulfilledAt,
        bytes memory wrappedDEK,
        bytes memory rawData,
        string memory note,
        bool fulfilled,
        bool hasWrappedDEK,
        bool hasRawData
    ) {
        ResponseEnvelope storage r = responses[requestId];
        return (
            r.status,
            r.locatorType,
            r.encrypted,
            r.locator,
            r.mimeType,
            r.schemaRef,
            r.contentHash,
            r.fulfilledAt,
            r.wrappedDEK,
            r.rawData,
            r.note,
            r.fulfilled,
            r.hasWrappedDEK,
            r.hasRawData
        );
    }

    function getResult(
        bytes32 requestId
    ) external view returns (
        uint8 status,
        uint8 locatorType,
        bool encrypted,
        string memory locator,
        string memory mimeType,
        string memory schemaRef,
        bytes32 contentHash,
        uint64 fulfilledAt,
        bytes memory wrappedDEK,
        bytes memory rawData,
        string memory note,
        bool fulfilled,
        bool hasWrappedDEK,
        bool hasRawData
    ) {
        return this.getResponse(requestId);
    }

    function getUserRequests(address user) external view returns (bytes32[] memory ids) {
        return userRequests[user];
    }

    function withdrawProviderLink(uint256 amount) external nonReentrant {
        uint256 bal = providerLinkBalance[msg.sender];
        require(amount <= bal, "amount>balance");
        providerLinkBalance[msg.sender] = bal - amount;
        totalProviderOwed -= amount;

        LinkTokenInterface link = LinkTokenInterface(chainlinkTokenAddress());
        require(link.transfer(msg.sender, amount), "LINK transfer failed");
        emit ProviderWithdrawn(msg.sender, amount);
    }

    function availableTreasuryLink() public view returns (uint256 amount) {
        uint256 balance = LinkTokenInterface(chainlinkTokenAddress()).balanceOf(address(this));
        if (balance <= totalProviderOwed) return 0;
        return balance - totalProviderOwed;
    }

    function withdrawLink(address to, uint256 amount) external onlyOwner {
        require(to != address(0), "to=0");
        require(availableTreasuryLink() >= amount, "Insufficient treasury LINK");
        LinkTokenInterface link = LinkTokenInterface(chainlinkTokenAddress());
        require(link.transfer(to, amount), "LINK transfer failed");
    }

    receive() external payable {}
}
