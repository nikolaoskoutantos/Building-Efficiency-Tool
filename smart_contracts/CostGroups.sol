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

    // Was constant JOB_UUID; now configurable so you can change without redeploy
    string public jobUUID;

    // -------- Global catalog price --------
    uint256 public catalogPriceJuels;

    // -------- Provider payout wallet (for now: just a wallet) --------
    address public payoutWallet;

    // -------- Public key registry --------
    mapping(address => bytes) private pubKeyByWallet;

    // -------- Tier model --------
    struct Tier {
        uint256 periodSec;
        uint256 priceJuels;
        uint32 maxRequests;
        uint32[] productIds; // empty = full catalog (tier meaning)
        bool active;
    }
    mapping(uint8 => Tier) public tiers;

    struct Subscription {
        uint64 expiresAt;
        uint32 remainingRequests;
    }
    mapping(address => Subscription) public subs;

    // -------- Product catalog --------
    struct Product {
        string query;
        bool active;
    }
    mapping(uint32 => Product) public products;

    uint32[] private productIndex;
    mapping(uint32 => bool) private productIndexed;

    // -------- Purchase tracking --------
    struct Purchase {
        address buyer;
        uint32[] productIds;
        uint256 paidJuels;
        uint64 purchasedAt;
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
    event ProductUpdated(uint32 indexed productId, bool active);
    event ProductsRequested(bytes32 indexed requestId, address indexed user, uint32 count, uint256 paidJuels);
    event CostsCIDFulfilled(bytes32 indexed requestId, address indexed user, string cid, uint64 fulfilledAt, bool hasWrappedDEK);
    event PubKeySet(address indexed user, bytes pubKey);

    // --- New ops events ---
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

    // ---------------- Constructor (UPDATED) ----------------
    // jobId now comes as string (UUID with or without hyphens) and is converted to bytes32.
    constructor(
        address _linkToken,
        address _operator,
        string memory _jobIdStr,   // <-- changed from bytes32 to string
        uint256 _feeJuels
    ) {
        _setChainlinkToken(_linkToken);
        _setChainlinkOracle(_operator);

        if (_operator == address(0)) revert ZeroAddress();

        operator = _operator;
        jobId = _jobIdFromString(_jobIdStr); // <-- conversion here
        feeJuels = _feeJuels;

        // initial default (same as your original constant)
        jobUUID = "5c1acaa7-7fe9-47b8-8c9d-e5be418e9cdc";
    }

    // ---------------- Internal helper: string UUID -> bytes32 ----------------
    // Accepts:
    // - 32 chars: "4673f9aa277e45c28d83c8f5642fae6c"
    // - 36 chars: "4673f9aa-277e-45c2-8d83-c8f5642fae6c"
    function _jobIdFromString(string memory s) internal pure returns (bytes32) {
        bytes memory b = bytes(s);
        require(b.length == 32 || b.length == 36, "jobId must be 32 or 36 chars");

        bytes memory out = new bytes(32);
        uint256 j = 0;

        for (uint256 i = 0; i < b.length; i++) {
            bytes1 c = b[i];

            if (c == 0x2d) { // '-'
                require(b.length == 36, "hyphens only in 36-char UUID");
                continue;
            }

            bool isHex =
                (c >= 0x30 && c <= 0x39) || // 0-9
                (c >= 0x61 && c <= 0x66) || // a-f
                (c >= 0x41 && c <= 0x46);   // A-F
            require(isHex, "non-hex char");

            require(j < 32, "jobId too long");
            out[j++] = c;
        }

        require(j == 32, "jobId must resolve to 32 chars");

        bytes32 job;
        assembly { job := mload(add(out, 32)) }
        return job;
    }

    // ---------------- Admin (existing) ----------------
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
        tiers[id] = Tier(periodSec, priceJuels, maxRequests, productIds, active);
        emit TierUpdated(id);
    }

    function setProduct(
        uint32 productId,
        string calldata query,
        bool active
    ) external onlyOwner {
        require(productId != 0, "productId=0");

        products[productId] = Product(query, active);

        if (!productIndexed[productId]) {
            productIndexed[productId] = true;
            productIndex.push(productId);
        }

        emit ProductUpdated(productId, active);
    }

    function setPubKey(address user, bytes calldata pubKey) external onlyOwner {
        pubKeyByWallet[user] = pubKey;
        emit PubKeySet(user, pubKey);
    }

    // ---------------- Admin (NEW ops setters) ----------------
    function setJobId(bytes32 newJobId) external onlyOwner {
        emit JobIdUpdated(jobId, newJobId);
        jobId = newJobId;
    }

    function setOperator(address newOperator) external onlyOwner {
        if (newOperator == address(0)) revert ZeroAddress();
        emit OperatorUpdated(operator, newOperator);
        operator = newOperator;

        // keep ChainlinkClient oracle in sync
        _setChainlinkOracle(newOperator);
    }

    function setFeeJuels(uint256 newFeeJuels) external onlyOwner {
        emit FeeUpdated(feeJuels, newFeeJuels);
        feeJuels = newFeeJuels;
    }

    // convenience setter (still useful post-deploy)
    function setJobIdFromString(string calldata s) external onlyOwner {
        bytes32 old = jobId;
        bytes32 converted = _jobIdFromString(s);
        emit JobIdUpdated(old, converted);
        jobId = converted;
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

    // ---------------- Subscribe (unchanged) ----------------
    function subscribe(uint8 tierId) external nonReentrant whenNotPaused {
        Tier memory t = tiers[tierId];
        require(t.active, "tier inactive");

        LinkTokenInterface link = LinkTokenInterface(_chainlinkTokenAddress());
        require(link.transferFrom(msg.sender, address(this), t.priceJuels), "payment failed");

        subs[msg.sender] = Subscription(
            uint64(block.timestamp + t.periodSec),
            t.maxRequests
        );

        emit Subscribed(msg.sender, tierId);
    }

    // ---------------- Request (unchanged logic) ----------------
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

        Subscription storage s = subs[msg.sender];
        uint256 charged = 0;

        if (s.expiresAt >= block.timestamp && s.remainingRequests > 0) {
            s.remainingRequests -= 1;
        } else {
            require(catalogPriceJuels > 0, "catalog price not set");
            require(link.transferFrom(msg.sender, address(this), catalogPriceJuels), "payment failed");
            charged = catalogPriceJuels;
        }

        uint32[] memory ids = new uint32[](productIds.length);
        for (uint256 i = 0; i < productIds.length; i++) {
            ids[i] = productIds[i];
        }

        Chainlink.Request memory req = _buildChainlinkRequest(
            jobId,
            address(this),
            this.fulfillCostsCID.selector
        );

        string memory pubKeyHex = _bytesToHexString(pubKeyByWallet[msg.sender]);
        string memory productIdsJson = _uint32ArrayToJson(ids);

        string memory body = string(
            abi.encodePacked(
                "{\"job_id\":\"", jobUUID, "\",",
                "\"buyer\":\"", _addressToHexString(msg.sender), "\",",
                "\"pubKey\":\"", pubKeyHex, "\",",
                "\"productIds\":", productIdsJson,
                "}"
            )
        );

        Chainlink._add(req, "requestData", body);
        Chainlink._add(req, "path", "data");

        reqId = _sendChainlinkRequestTo(operator, req, feeJuels);
        latestRequestId = reqId;

        purchases[reqId] = Purchase(msg.sender, ids, charged, uint64(block.timestamp));
        userRequests[msg.sender].push(reqId);

        emit ProductsRequested(reqId, msg.sender, uint32(ids.length), charged);
    }

    // ---------------- Fulfillment (unchanged) ----------------
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
        returns (address buyer, uint32[] memory productIds, uint256 paidJuels, uint64 purchasedAt)
    {
        Purchase storage p = purchases[requestId_];

        uint32[] memory ids = new uint32[](p.productIds.length);
        for (uint256 i = 0; i < p.productIds.length; i++) ids[i] = p.productIds[i];

        return (p.buyer, ids, p.paidJuels, p.purchasedAt);
    }

    function getResult(bytes32 requestId_)
        external
        view
        returns (string memory cid, uint64 fulfilledAt, bytes memory wrappedDEK, bool fulfilled, bool hasWrappedDEK)
    {
        Result storage r = resultByRequest[requestId_];
        return (r.cid, r.fulfilledAt, r.wrappedDEK, r.fulfilled, r.hasWrappedDEK);
    }

    function getRequestOverview(bytes32 requestId_)
        external
        view
        returns (
            address buyer,
            uint256 paidJuels,
            uint64 purchasedAt,
            uint32 productCount,
            string memory cid,
            uint64 fulfilledAt,
            bool fulfilled,
            bool hasWrappedDEK
        )
    {
        Purchase storage p = purchases[requestId_];
        Result storage r = resultByRequest[requestId_];
        return (
            p.buyer,
            p.paidJuels,
            p.purchasedAt,
            uint32(p.productIds.length),
            r.cid,
            r.fulfilledAt,
            r.fulfilled,
            r.hasWrappedDEK
        );
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