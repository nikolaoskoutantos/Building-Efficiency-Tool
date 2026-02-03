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
    address public operator;
    bytes32 public jobId;
    uint256 public feeJuels;

    // Adapter-level job UUID (string) included in request body
    string public jobUUID;

    // -------- Pricing --------
    // Pricing rule (as discussed):
    // - productIds == []  => whole catalog => charge catalogPriceJuels (flat)
    // - productIds != []  => charge sum(product.priceJuels) for requested products
    uint256 public catalogPriceJuels;

    // -------- Provider payout wallet (optional) --------
    address public payoutWallet;

    // -------- Public key registry --------
    mapping(address => bytes) private pubKeyByWallet;

    // -------- Tier model (Option 2 subscription) --------
    // - tier.productIds empty => full catalog included under subscription
    // - tier.productIds non-empty => only those products included (free), excluded products charged per-product
    struct Tier {
        uint256 periodSec;
        uint256 priceJuels;
        uint32 maxRequests;
        uint32[] productIds; // empty => full catalog included
        bool active;
    }
    mapping(uint8 => Tier) public tiers;

    // Fast membership check for restricted tiers
    mapping(uint8 => mapping(uint32 => bool)) private tierIncludesProduct;

    struct Subscription {
        uint64 expiresAt;
        uint32 remainingRequests;
        uint8 tierId;
    }
    mapping(address => Subscription) public subs;

    // -------- Product catalog --------
    struct Product {
        string query;
        uint256 priceJuels; // per-product on-demand price
        bool active;
    }
    mapping(uint32 => Product) public products;

    // Index to support "all products" expansion for oracle requests
    uint32[] private productIndex;
    mapping(uint32 => bool) private productIndexed;

    // -------- Purchase tracking --------
    struct Purchase {
        address buyer;
        uint32[] productIdsExpanded; // the actual list sent to the oracle (expanded if full catalog)
        bool fullCatalogRequested;   // original request was productIds == []
        uint256 paidJuels;
        uint64 purchasedAt;
        uint8 tierIdUsed;
        bool subscriptionUsed;
    }
    mapping(bytes32 => Purchase) private purchases;

    // -------- Results --------
    struct Result {
        string cid;
        uint64 fulfilledAt;
        bytes wrappedDEK;
        bool fulfilled;
        bool hasWrappedDEK;
    }
    mapping(bytes32 => Result) private resultByRequest;
    mapping(address => bytes32[]) private userRequests;

    // -------- Convenience --------
    string public latestCID;
    bytes32 public latestRequestId;

    // -------- Events --------
    event TierUpdated(uint8 indexed id);
    event Subscribed(address indexed user, uint8 indexed tierId);
    event ProductUpdated(uint32 indexed productId, bool active, uint256 priceJuels);
    event ProductsRequested(
        bytes32 indexed requestId,
        address indexed user,
        uint32 expandedCount,
        bool fullCatalogRequested,
        uint256 paidJuels,
        bool subscriptionUsed,
        uint8 tierIdUsed
    );
    event CostsCIDFulfilled(bytes32 indexed requestId, address indexed user, string cid, uint64 fulfilledAt, bool hasWrappedDEK);
    event PubKeySet(address indexed user, bytes pubKey);

    // Ops events
    event JobIdUpdated(bytes32 indexed oldJobId, bytes32 indexed newJobId);
    event OperatorUpdated(address indexed oldOperator, address indexed newOperator);
    event FeeUpdated(uint256 oldFeeJuels, uint256 newFeeJuels);
    event JobUUIDUpdated(string oldJobUUID, string newJobUUID);
    event PayoutWalletUpdated(address indexed oldWallet, address indexed newWallet);
    event LinkWithdrawn(address indexed to, uint256 amount);
    event NativeWithdrawn(address indexed to, uint256 amount);

    // -------- Errors --------
    error ZeroAddress();
    error LinkTransferFailed();

    // ---------------- Constructor ----------------
    constructor(
        address _linkToken,
        address _operator,
        bytes32 _jobId,
        uint256 _feeJuels
    ) {
        _setChainlinkToken(_linkToken);
        _setChainlinkOracle(_operator);

        if (_operator == address(0)) revert ZeroAddress();

        operator = _operator;
        jobId = _jobId;
        feeJuels = _feeJuels;

        jobUUID = "5c1acaa7-7fe9-47b8-8c9d-e5be418e9cdc";
    }

    // ---------------- Admin ----------------
    function setCatalogPrice(uint256 price) external onlyOwner {
        catalogPriceJuels = price;
    }

    function setTier(
        uint8 id,
        uint256 periodSec,
        uint256 priceJuels,
        uint32 maxRequests,
        uint32[] calldata productIds,
        bool active
    ) external onlyOwner {
        // clear previous membership if it was a restricted tier
        Tier storage oldTier = tiers[id];
        if (oldTier.productIds.length > 0) {
            for (uint256 i = 0; i < oldTier.productIds.length; i++) {
                tierIncludesProduct[id][oldTier.productIds[i]] = false;
            }
        }

        tiers[id] = Tier(periodSec, priceJuels, maxRequests, productIds, active);

        // set membership if restricted tier
        if (productIds.length > 0) {
            for (uint256 i = 0; i < productIds.length; i++) {
                tierIncludesProduct[id][productIds[i]] = true;
            }
        }

        emit TierUpdated(id);
    }

    function setProduct(
        uint32 productId,
        string calldata query,
        uint256 priceJuels,
        bool active
    ) external onlyOwner {
        require(productId != 0, "productId=0");

        products[productId] = Product(query, priceJuels, active);

        if (!productIndexed[productId]) {
            productIndexed[productId] = true;
            productIndex.push(productId);
        }

        emit ProductUpdated(productId, active, priceJuels);
    }

    function setPubKey(address user, bytes calldata pubKey) external onlyOwner {
        pubKeyByWallet[user] = pubKey;
        emit PubKeySet(user, pubKey);
    }

    // ---------------- Admin ops setters ----------------
    function setJobId(bytes32 newJobId) external onlyOwner {
        emit JobIdUpdated(jobId, newJobId);
        jobId = newJobId;
    }

    function setOperator(address newOperator) external onlyOwner {
        if (newOperator == address(0)) revert ZeroAddress();
        emit OperatorUpdated(operator, newOperator);
        operator = newOperator;
        _setChainlinkOracle(newOperator);
    }

    function setFeeJuels(uint256 newFeeJuels) external onlyOwner {
        emit FeeUpdated(feeJuels, newFeeJuels);
        feeJuels = newFeeJuels;
    }

    function setJobUUID(string calldata newJobUUID) external onlyOwner {
        emit JobUUIDUpdated(jobUUID, newJobUUID);
        jobUUID = newJobUUID;
    }

    function setPayoutWallet(address newWallet) external onlyOwner {
        if (newWallet == address(0)) revert ZeroAddress();
        emit PayoutWalletUpdated(payoutWallet, newWallet);
        payoutWallet = newWallet;
    }

    // ---------------- Subscribe ----------------
    function subscribe(uint8 tierId) external nonReentrant whenNotPaused {
        Tier memory t = tiers[tierId];
        require(t.active, "tier inactive");

        LinkTokenInterface link = LinkTokenInterface(_chainlinkTokenAddress());
        require(link.transferFrom(msg.sender, address(this), t.priceJuels), "payment failed");

        subs[msg.sender] = Subscription(
            uint64(block.timestamp + t.periodSec),
            t.maxRequests,
            tierId
        );

        emit Subscribed(msg.sender, tierId);
    }

    // =========================================================
    // Request
    // =========================================================
    function requestProductsCID(uint32[] calldata productIds)
        external
        nonReentrant
        whenNotPaused
        returns (bytes32 reqId)
    {
        require(jobId != 0x0, "jobId not set");
        require(operator != address(0), "operator not set");

        LinkTokenInterface link = LinkTokenInterface(_chainlinkTokenAddress());
        require(link.balanceOf(address(this)) >= feeJuels, "Insufficient LINK for fee");

        bool fullCatalogRequested = (productIds.length == 0);

        // Expand list for oracle request: [] => all active products
        uint32[] memory expanded = _expandForOracle(productIds);

        // Compute/collect charge based on the rule you specified + subscription option2
        (uint256 charged, bool subscriptionUsed, uint8 tierIdUsed) =
            _computeAndCollectCharge(msg.sender, productIds, fullCatalogRequested);

        // Build Chainlink request
        Chainlink.Request memory req = _buildChainlinkRequest(
            jobId,
            address(this),
            this.fulfillCostsCID.selector
        );

        string memory body = _buildRequestBody(msg.sender, expanded);

        Chainlink._add(req, "requestData", body);
        Chainlink._add(req, "path", "data");

        reqId = _sendChainlinkRequestTo(operator, req, feeJuels);
        latestRequestId = reqId;

        purchases[reqId] = Purchase(
            msg.sender,
            expanded,
            fullCatalogRequested,
            charged,
            uint64(block.timestamp),
            tierIdUsed,
            subscriptionUsed
        );

        userRequests[msg.sender].push(reqId);

        emit ProductsRequested(
            reqId,
            msg.sender,
            uint32(expanded.length),
            fullCatalogRequested,
            charged,
            subscriptionUsed,
            tierIdUsed
        );
    }

    // =========================================================
    // Pricing logic (matches your rule)
    //
    // No subscription:
    // - full catalog request => catalogPriceJuels
    // - specific request     => sum(product.priceJuels)
    //
    // With subscription:
    // - consume 1 request
    // - if tier is full catalog (tier.productIds empty) => charge 0 regardless of request type
    // - else (restricted tier):
    //    - full catalog request => charge sum(price of ALL products NOT included)
    //    - specific request     => charge sum(price of requested products NOT included)
    // =========================================================
    function _computeAndCollectCharge(
        address buyer,
        uint32[] calldata productIds,
        bool fullCatalogRequested
    ) internal returns (uint256 charged, bool subscriptionUsed, uint8 tierIdUsed) {
        Subscription storage s = subs[buyer];
        subscriptionUsed = (s.expiresAt >= block.timestamp && s.remainingRequests > 0);
        tierIdUsed = subscriptionUsed ? s.tierId : 0;

        if (subscriptionUsed) {
            s.remainingRequests -= 1;

            Tier storage tier = tiers[tierIdUsed];

            // Full catalog included under subscription
            if (tier.productIds.length == 0) {
                return (0, true, tierIdUsed);
            }

            // Restricted tier: included free, excluded charged (per-product)
            if (fullCatalogRequested) {
                // charge all active products not included
                for (uint256 i = 0; i < productIndex.length; i++) {
                    uint32 pid = productIndex[i];
                    Product storage p = products[pid];
                    if (!p.active) continue;

                    if (!tierIncludesProduct[tierIdUsed][pid]) {
                        charged += p.priceJuels;
                    }
                }
            } else {
                // charge only requested products not included
                for (uint256 i = 0; i < productIds.length; i++) {
                    uint32 pid = productIds[i];
                    Product storage p = products[pid];
                    require(p.active, "product inactive");
                    if (!tierIncludesProduct[tierIdUsed][pid]) {
                        charged += p.priceJuels;
                    }
                }
            }

            if (charged > 0) {
                LinkTokenInterface link = LinkTokenInterface(_chainlinkTokenAddress());
                require(link.transferFrom(buyer, address(this), charged), "payment failed");
            }

            return (charged, true, tierIdUsed);
        }

        // No subscription
        if (fullCatalogRequested) {
            require(catalogPriceJuels > 0, "catalog price not set");
            charged = catalogPriceJuels;
        } else {
            for (uint256 i = 0; i < productIds.length; i++) {
                uint32 pid = productIds[i];
                Product storage p = products[pid];
                require(p.active, "product inactive");
                charged += p.priceJuels;
            }
        }

        if (charged > 0) {
            LinkTokenInterface link = LinkTokenInterface(_chainlinkTokenAddress());
            require(link.transferFrom(buyer, address(this), charged), "payment failed");
        }

        return (charged, false, 0);
    }

    // Expand [] to "all active products" for the oracle request body
    function _expandForOracle(uint32[] calldata productIds) internal view returns (uint32[] memory out) {
        if (productIds.length > 0) {
            out = new uint32[](productIds.length);
            for (uint256 i = 0; i < productIds.length; i++) out[i] = productIds[i];
            return out;
        }

        // count active
        uint256 activeCount = 0;
        for (uint256 i = 0; i < productIndex.length; i++) {
            uint32 pid = productIndex[i];
            if (products[pid].active) activeCount++;
        }

        out = new uint32[](activeCount);
        uint256 k = 0;
        for (uint256 i = 0; i < productIndex.length; i++) {
            uint32 pid = productIndex[i];
            if (products[pid].active) out[k++] = pid;
        }
    }

    function _buildRequestBody(address buyer, uint32[] memory ids) internal view returns (string memory) {
        string memory pubKeyHex = _bytesToHexString(pubKeyByWallet[buyer]);
        string memory productIdsJson = _uint32ArrayToJson(ids);

        return string(
            abi.encodePacked(
                "{\"job_id\":\"", jobUUID, "\",",
                "\"buyer\":\"", _addressToHexString(buyer), "\",",
                "\"pubKey\":\"", pubKeyHex, "\",",
                "\"productIds\":", productIdsJson,
                "}"
            )
        );
    }

    // ---------------- Fulfillment ----------------
    function fulfillCostsCID(bytes32 _requestId, bytes memory _data)
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

        latestCID = cid;

        address buyer = purchases[_requestId].buyer;
        emit CostsCIDFulfilled(_requestId, buyer, cid, r.fulfilledAt, r.hasWrappedDEK);
    }

    // ---------------- Query methods ----------------
    function getUserRequestsCount(address user) external view returns (uint256) {
        return userRequests[user].length;
    }

    function getUserRequests(address user, uint256 offset, uint256 limit)
        external
        view
        returns (bytes32[] memory out)
    {
        bytes32[] storage arr = userRequests[user];
        uint256 n = arr.length;

        if (offset > n) offset = n;

        uint256 end = offset + limit;
        if (end > n) end = n;

        uint256 m = end - offset;
        out = new bytes32[](m);

        for (uint256 i = 0; i < m; i++) {
            out[i] = arr[offset + i];
        }
    }

    function getPurchase(bytes32 requestId_)
        external
        view
        returns (
            address buyer,
            uint32[] memory productIdsExpanded,
            bool fullCatalogRequested,
            uint256 paidJuels,
            uint64 purchasedAt,
            bool subscriptionUsed,
            uint8 tierIdUsed
        )
    {
        Purchase storage p = purchases[requestId_];

        uint32[] memory ids = new uint32[](p.productIdsExpanded.length);
        for (uint256 i = 0; i < p.productIdsExpanded.length; i++) ids[i] = p.productIdsExpanded[i];

        return (p.buyer, ids, p.fullCatalogRequested, p.paidJuels, p.purchasedAt, p.subscriptionUsed, p.tierIdUsed);
    }

    function getResult(bytes32 requestId_)
        external
        view
        returns (string memory cid, uint64 fulfilledAt, bytes memory wrappedDEK, bool fulfilled, bool hasWrappedDEK)
    {
        Result storage r = resultByRequest[requestId_];
        return (r.cid, r.fulfilledAt, r.wrappedDEK, r.fulfilled, r.hasWrappedDEK);
    }

    // ---------------- Balance + withdrawals ----------------
    function linkBalance() public view returns (uint256) {
        return LinkTokenInterface(_chainlinkTokenAddress()).balanceOf(address(this));
    }

    function nativeBalance() public view returns (uint256) {
        return address(this).balance;
    }

    function _withdrawLink(address to, uint256 amount) internal {
        if (to == address(0)) revert ZeroAddress();
        LinkTokenInterface link = LinkTokenInterface(_chainlinkTokenAddress());
        if (!link.transfer(to, amount)) revert LinkTransferFailed();
        emit LinkWithdrawn(to, amount);
    }

    function withdrawLink(address to, uint256 amount) external onlyOwner nonReentrant {
        _withdrawLink(to, amount);
    }

    function withdrawAllLink(address to) external onlyOwner nonReentrant {
        _withdrawLink(to, linkBalance());
    }

    function withdrawRevenueToPayoutWallet(uint256 amount) external onlyOwner nonReentrant {
        require(payoutWallet != address(0), "payoutWallet not set");
        _withdrawLink(payoutWallet, amount);
    }

    function withdrawNative(address payable to, uint256 amount) external onlyOwner nonReentrant {
        if (to == address(0)) revert ZeroAddress();
        (bool ok, ) = to.call{value: amount}("");
        require(ok, "native transfer failed");
        emit NativeWithdrawn(to, amount);
    }

    // ---------------- Utils ----------------
    function _uint32ArrayToJson(uint32[] memory arr) internal pure returns (string memory) {
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
