// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Chainlink, ChainlinkClient} from "@chainlink/contracts/src/v0.8/operatorforwarder/ChainlinkClient.sol";
import {LinkTokenInterface} from "@chainlink/contracts/src/v0.8/interfaces/LinkTokenInterface.sol";

import "https://raw.githubusercontent.com/OpenZeppelin/openzeppelin-contracts/v4.9.6/contracts/access/Ownable.sol";
import "https://raw.githubusercontent.com/OpenZeppelin/openzeppelin-contracts/v4.9.6/contracts/security/Pausable.sol";
import "https://raw.githubusercontent.com/OpenZeppelin/openzeppelin-contracts/v4.9.6/contracts/security/ReentrancyGuard.sol";

contract MarketplaceCIDRequester is ChainlinkClient, Ownable, Pausable, ReentrancyGuard {
    using Chainlink for Chainlink.Request;

    // ---------------- Errors ----------------
    error ZeroAddress();
    error NotActive();
    error UnknownService();
    error UnknownProduct();
    error ProductNotInService();
    error InsufficientLinkForOracleFee();
    error PaymentFailed();
    error LinkTransferFailed();
    error TierInactive();
    error InvalidTier();
    error TooManyProducts();

    // ---------------- Config ----------------
    uint32 public constant MAX_PRODUCTS_PER_REQUEST = 200;

    // ---------------- Public key registry (optional) ----------------
    mapping(address => bytes) private pubKeyByWallet;
    event PubKeySet(address indexed user, bytes pubKey);

    function setPubKey(address user, bytes calldata pubKey) external onlyOwner {
        pubKeyByWallet[user] = pubKey;
        emit PubKeySet(user, pubKey);
    }

    // ---------------- Service catalog ----------------
    struct Service {
        address operator;
        bytes32 jobId;
        uint256 feeJuels;                // oracle fee per request
        uint256 defaultUnitPriceJuels;   // per-product on-demand default
        address defaultPayoutWallet;
        string data;
        string description;
        bool active;
    }

    mapping(uint32 => Service) public services;
    event ServiceUpserted(uint32 indexed serviceId, bool active);

    function upsertService(
        uint32 serviceId,
        address operator,
        bytes32 jobId,
        uint256 feeJuels,
        uint256 defaultUnitPriceJuels,
        address defaultPayoutWallet,
        string calldata data,
        string calldata description,
        bool active
    ) external onlyOwner {
        if (serviceId == 0) revert UnknownService();
        if (operator == address(0)) revert ZeroAddress();
        if (defaultPayoutWallet == address(0)) revert ZeroAddress();

        services[serviceId] = Service({
            operator: operator,
            jobId: jobId,
            feeJuels: feeJuels,
            defaultUnitPriceJuels: defaultUnitPriceJuels,
            defaultPayoutWallet: defaultPayoutWallet,
            data: data,
            description: description,
            active: active
        });

        emit ServiceUpserted(serviceId, active);
    }

    // ---------------- Products ----------------
    struct Product {
        uint32 serviceId;
        string query;
        uint256 priceOverrideJuels;        // 0 => use service.defaultUnitPriceJuels
        address payoutOverrideWallet;      // 0 => use service.defaultPayoutWallet
        bool active;
    }

    mapping(uint32 => Product) public products;
    event ProductUpserted(uint32 indexed productId, uint32 indexed serviceId, bool active);

    function upsertProduct(
        uint32 productId,
        uint32 serviceId,
        string calldata query,
        uint256 priceOverrideJuels,
        address payoutOverrideWallet,
        bool active
    ) external onlyOwner {
        if (productId == 0) revert UnknownProduct();
        if (services[serviceId].operator == address(0)) revert UnknownService();

        products[productId] = Product({
            serviceId: serviceId,
            query: query,
            priceOverrideJuels: priceOverrideJuels,
            payoutOverrideWallet: payoutOverrideWallet,
            active: active
        });

        emit ProductUpserted(productId, serviceId, active);
    }

    // ---------------- Tiers (Option 2) ----------------
    struct Tier {
        uint256 periodSec;
        uint256 priceJuels;
        uint32 maxRequests;
        bool active;

        mapping(uint32 => bool) includesProduct;
        uint32[] includedList; // UI only
    }

    mapping(uint32 => mapping(uint8 => Tier)) private tiersByService;
    event TierUpserted(uint32 indexed serviceId, uint8 indexed tierId, bool active);

    function setTier(
        uint32 serviceId,
        uint8 tierId,
        uint256 periodSec,
        uint256 priceJuels,
        uint32 maxRequests,
        uint32[] calldata includedProductIds,
        bool active
    ) external onlyOwner {
        if (services[serviceId].operator == address(0)) revert UnknownService();

        Tier storage t = tiersByService[serviceId][tierId];
        t.periodSec = periodSec;
        t.priceJuels = priceJuels;
        t.maxRequests = maxRequests;
        t.active = active;

        // clear old membership
        uint32[] storage prev = t.includedList;
        for (uint256 i = 0; i < prev.length; i++) {
            t.includesProduct[prev[i]] = false;
        }
        delete t.includedList;

        // set new membership
        for (uint256 i = 0; i < includedProductIds.length; i++) {
            uint32 pid = includedProductIds[i];
            Product storage p = products[pid];
            if (p.serviceId != serviceId) revert ProductNotInService();
            t.includesProduct[pid] = true;
            t.includedList.push(pid);
        }

        emit TierUpserted(serviceId, tierId, active);
    }

    // ---------------- User subscriptions ----------------
    struct Subscription {
        uint64 expiresAt;
        uint32 remainingRequests;
        uint8 tierId;
    }

    mapping(address => mapping(uint32 => Subscription)) public subs;
    event Subscribed(address indexed user, uint32 indexed serviceId, uint8 indexed tierId, uint64 expiresAt, uint32 remainingRequests);

    function subscribe(uint32 serviceId, uint8 tierId) external nonReentrant whenNotPaused {
        Service storage svc = services[serviceId];
        if (!svc.active) revert NotActive();

        Tier storage t = tiersByService[serviceId][tierId];
        if (!t.active) revert TierInactive();
        if (t.periodSec == 0) revert InvalidTier();

        LinkTokenInterface link = LinkTokenInterface(_chainlinkTokenAddress());
        if (!link.transferFrom(msg.sender, address(this), t.priceJuels)) revert PaymentFailed();

        subs[msg.sender][serviceId] = Subscription({
            expiresAt: uint64(block.timestamp + t.periodSec),
            remainingRequests: t.maxRequests,
            tierId: tierId
        });

        emit Subscribed(msg.sender, serviceId, tierId, uint64(block.timestamp + t.periodSec), t.maxRequests);
    }

    // ---------------- Provider payouts (LINK ledger) ----------------
    mapping(address => uint256) public providerLinkBalance;
    event ProviderCredited(address indexed provider, uint256 amount);
    event ProviderWithdrawn(address indexed provider, uint256 amount);

    function withdrawProviderLink(uint256 amount) external nonReentrant {
        uint256 bal = providerLinkBalance[msg.sender];
        require(amount <= bal, "amount>balance");
        providerLinkBalance[msg.sender] = bal - amount;

        LinkTokenInterface link = LinkTokenInterface(_chainlinkTokenAddress());
        if (!link.transfer(msg.sender, amount)) revert LinkTransferFailed();

        emit ProviderWithdrawn(msg.sender, amount);
    }

    // ---------------- Purchases + results ----------------
    struct Purchase {
        address buyer;
        uint32 serviceId;
        uint32[] productIds;
        uint256 paidJuels;       // marketplace charge (not oracle fee)
        uint64 purchasedAt;
        uint8 tierIdUsed;        // 0 if none
        bool subscriptionUsed;
    }

    mapping(bytes32 => Purchase) public purchases;

    struct Result {
        string cid;
        uint64 fulfilledAt;
        bytes wrappedDEK;
        bool fulfilled;
        bool hasWrappedDEK;
    }

    mapping(bytes32 => Result) public resultByRequest;
    mapping(address => bytes32[]) public userRequests;

    event ProductsRequested(bytes32 indexed requestId, address indexed user, uint32 indexed serviceId, uint32 count, uint256 paidJuels, uint8 tierIdUsed, bool subscriptionUsed);
    event CIDFulfilled(bytes32 indexed requestId, address indexed user, string cid, uint64 fulfilledAt, bool hasWrappedDEK);

    // =========================================================
    // Main request (thin function to avoid stack-too-deep)
    // =========================================================
    function requestProductsCID(uint32 serviceId, uint32[] calldata productIds)
        external
        nonReentrant
        whenNotPaused
        returns (bytes32 reqId)
    {
        uint256 n = productIds.length;
        if (n == 0 || n > MAX_PRODUCTS_PER_REQUEST) revert TooManyProducts();

        Service storage svc = services[serviceId];
        if (svc.operator == address(0)) revert UnknownService();
        if (!svc.active) revert NotActive();
        if (svc.jobId == 0x0) revert UnknownService();

        LinkTokenInterface link = LinkTokenInterface(_chainlinkTokenAddress());
        if (link.balanceOf(address(this)) < svc.feeJuels) revert InsufficientLinkForOracleFee();

        // pricing + validation + subscription decrement happens here
        (uint256 charged, bool onlyExcluded, uint8 tierIdUsed, bool subscriptionUsed) =
            _applyPricingAndValidate(serviceId, msg.sender, productIds);

        if (charged > 0) {
            if (!link.transferFrom(msg.sender, address(this), charged)) revert PaymentFailed();
            _creditProvidersForRequest(serviceId, productIds, charged, onlyExcluded, tierIdUsed);
        }

        // build and send Chainlink request (body building isolated)
        reqId = _sendOracleRequest(serviceId, msg.sender, productIds);

        // store purchase metadata
        uint32[] memory ids = new uint32[](n);
        for (uint256 i = 0; i < n; i++) ids[i] = productIds[i];

        purchases[reqId] = Purchase({
            buyer: msg.sender,
            serviceId: serviceId,
            productIds: ids,
            paidJuels: charged,
            purchasedAt: uint64(block.timestamp),
            tierIdUsed: tierIdUsed,
            subscriptionUsed: subscriptionUsed
        });

        userRequests[msg.sender].push(reqId);

        emit ProductsRequested(reqId, msg.sender, serviceId, uint32(n), charged, tierIdUsed, subscriptionUsed);
    }

    // =========================================================
    // Pricing + subscription logic (Option 2)
    // - If subscribed: included products free, excluded charged
    // - If not subscribed: all charged
    // =========================================================
    function _applyPricingAndValidate(
        uint32 serviceId,
        address buyer,
        uint32[] calldata productIds
    ) internal returns (uint256 charged, bool onlyExcluded, uint8 tierIdUsed, bool subscriptionUsed) {
        Subscription storage s = subs[buyer][serviceId];

        subscriptionUsed = (s.expiresAt >= block.timestamp && s.remainingRequests > 0);
        if (subscriptionUsed) {
            s.remainingRequests -= 1;
            tierIdUsed = s.tierId;
            onlyExcluded = true;

            Tier storage tier = tiersByService[serviceId][tierIdUsed];

            // included => free, excluded => charged
            for (uint256 i = 0; i < productIds.length; i++) {
                uint32 pid = productIds[i];
                Product storage p = products[pid];
                if (p.serviceId != serviceId) revert ProductNotInService();
                if (!p.active) revert NotActive();

                if (!tier.includesProduct[pid]) {
                    charged += _unitPriceForProduct(serviceId, pid);
                }
            }
        } else {
            tierIdUsed = 0;
            onlyExcluded = false;

            // all charged
            for (uint256 i = 0; i < productIds.length; i++) {
                uint32 pid = productIds[i];
                Product storage p = products[pid];
                if (p.serviceId != serviceId) revert ProductNotInService();
                if (!p.active) revert NotActive();

                charged += _unitPriceForProduct(serviceId, pid);
            }
        }
    }

    // =========================================================
    // Oracle request (isolated to avoid stack-too-deep)
    // =========================================================
    function _sendOracleRequest(
        uint32 serviceId,
        address buyer,
        uint32[] calldata productIds
    ) internal returns (bytes32 reqId) {
        Service storage svc = services[serviceId];

        Chainlink.Request memory req = _buildChainlinkRequest(
            svc.jobId,
            address(this),
            this.fulfill.selector
        );

        string memory body = _buildRequestBody(serviceId, buyer, productIds);
        Chainlink._add(req, "requestData", body);
        Chainlink._add(req, "path", "data");

        reqId = _sendChainlinkRequestTo(svc.operator, req, svc.feeJuels);
    }

    function _buildRequestBody(
        uint32 serviceId,
        address buyer,
        uint32[] calldata productIds
    ) internal view returns (string memory) {
        string memory pubKeyHex = _bytesToHexString(pubKeyByWallet[buyer]);
        string memory productIdsJson = _uint32ArrayToJson(productIds);

        return string(
            abi.encodePacked(
                "{",
                    "\"buyer\":\"", _addressToHexString(buyer), "\",",
                    "\"pubKey\":\"", pubKeyHex, "\",",
                    "\"serviceId\":", _uintToString(serviceId), ",",
                    "\"productIds\":", productIdsJson,
                "}"
            )
        );
    }

    // =========================================================
    // Provider crediting (refactored: loads from storage)
    // =========================================================
    function _unitPriceForProduct(uint32 serviceId, uint32 productId) internal view returns (uint256) {
        Product storage p = products[productId];
        Service storage svc = services[serviceId];
        if (p.priceOverrideJuels > 0) return p.priceOverrideJuels;
        return svc.defaultUnitPriceJuels;
    }

    function _payoutForProduct(uint32 serviceId, uint32 productId) internal view returns (address) {
        Product storage p = products[productId];
        Service storage svc = services[serviceId];
        if (p.payoutOverrideWallet != address(0)) return p.payoutOverrideWallet;
        return svc.defaultPayoutWallet;
    }

    function _creditProvidersForRequest(
        uint32 serviceId,
        uint32[] calldata productIds,
        uint256 totalCharged,
        bool onlyExcluded,
        uint8 tierIdUsed
    ) internal {
        if (totalCharged == 0) return;

        Tier storage tier = tiersByService[serviceId][tierIdUsed];

        uint256 denom = 0;
        for (uint256 i = 0; i < productIds.length; i++) {
            uint32 pid = productIds[i];
            if (onlyExcluded && tier.includesProduct[pid]) continue;
            denom += _unitPriceForProduct(serviceId, pid);
        }
        if (denom == 0) return;

        uint256 allocated = 0;
        for (uint256 i = 0; i < productIds.length; i++) {
            uint32 pid = productIds[i];
            if (onlyExcluded && tier.includesProduct[pid]) continue;

            uint256 u = _unitPriceForProduct(serviceId, pid);
            address pay = _payoutForProduct(serviceId, pid);

            uint256 share;
            if (i == productIds.length - 1) {
                share = totalCharged - allocated;
            } else {
                share = (totalCharged * u) / denom;
            }
            allocated += share;

            providerLinkBalance[pay] += share;
            emit ProviderCredited(pay, share);
        }
    }

    // ---------------- Fulfillment ----------------
    function fulfill(bytes32 _requestId, bytes memory _data)
        external
        recordChainlinkFulfillment(_requestId)
    {
        (string memory cid, bytes memory wrappedDEK) = abi.decode(_data, (string, bytes));

        Result storage r = resultByRequest[_requestId];
        r.cid = cid;
        r.fulfilledAt = uint64(block.timestamp);
        r.fulfilled = true;

        if (wrappedDEK.length > 0) {
            r.wrappedDEK = wrappedDEK;
            r.hasWrappedDEK = true;
        } else {
            r.hasWrappedDEK = false;
        }

        address buyer = purchases[_requestId].buyer;
        emit CIDFulfilled(_requestId, buyer, cid, r.fulfilledAt, r.hasWrappedDEK);
    }

    // ---------------- Admin withdrawals ----------------
    function linkBalance() public view returns (uint256) {
        return LinkTokenInterface(_chainlinkTokenAddress()).balanceOf(address(this));
    }

    function withdrawLink(address to, uint256 amount) external onlyOwner nonReentrant {
        if (to == address(0)) revert ZeroAddress();
        LinkTokenInterface link = LinkTokenInterface(_chainlinkTokenAddress());
        if (!link.transfer(to, amount)) revert LinkTransferFailed();
    }

    // ---------------- Utils ----------------
    function _uint32ArrayToJson(uint32[] calldata arr) internal pure returns (string memory) {
        bytes memory out = "[";
        for (uint256 i = 0; i < arr.length; i++) {
            out = abi.encodePacked(out, _uintToString(arr[i]));
            if (i < arr.length - 1) out = abi.encodePacked(out, ",");
        }
        out = abi.encodePacked(out, "]");
        return string(out);
    }

    function _uintToString(uint256 v) internal pure returns (string memory) {
        if (v == 0) return "0";
        uint256 j = v;
        uint256 len;
        while (j != 0) { len++; j /= 10; }
        bytes memory bstr = new bytes(len);
        uint256 k = len;
        j = v;
        while (j != 0) {
            bstr[--k] = bytes1(uint8(48 + j % 10));
            j /= 10;
        }
        return string(bstr);
    }

    function _addressToHexString(address a) internal pure returns (string memory) {
        bytes20 value = bytes20(a);
        bytes16 hexSymbols = "0123456789abcdef";
        bytes memory str = new bytes(2 + 40);
        str[0] = "0";
        str[1] = "x";
        for (uint256 i = 0; i < 20; i++) {
            str[2 + i*2] = hexSymbols[uint8(value[i] >> 4)];
            str[3 + i*2] = hexSymbols[uint8(value[i] & 0x0f)];
        }
        return string(str);
    }

    function _bytesToHexString(bytes memory data) internal pure returns (string memory) {
        if (data.length == 0) return "";
        bytes16 hexSymbols = "0123456789abcdef";
        bytes memory str = new bytes(2 + data.length * 2);
        str[0] = "0";
        str[1] = "x";
        for (uint256 i = 0; i < data.length; i++) {
            str[2 + i*2] = hexSymbols[uint8(data[i] >> 4)];
            str[3 + i*2] = hexSymbols[uint8(data[i] & 0x0f)];
        }
        return string(str);
    }

    receive() external payable {}
}
