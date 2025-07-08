// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "https://github.com/smartcontractkit/chainlink/blob/develop/contracts/src/v0.8/functions/v1_0_0/FunctionsClient.sol";
import "https://github.com/smartcontractkit/chainlink/blob/develop/contracts/src/v0.8/functions/v1_0_0/libraries/FunctionsRequest.sol";

contract WeatherCIDRegistry is FunctionsClient {
    using FunctionsRequest for FunctionsRequest.Request;

    address public admin;
    uint256 public requestFee = 0.01 ether;
    string public apiBaseUrl;

    mapping(bytes32 => string[]) public cidHistory;
    mapping(bytes32 => string) public latestCID;
    mapping(bytes32 => mapping(address => bool)) public locationAccess;

    mapping(bytes32 => bytes32) public requestIdToKey;
    mapping(bytes32 => address) public requestInitiator;
    mapping(address => mapping(bytes32 => string[])) private userCIDs;

    event CIDStored(string dataType, string lat, string lon, string cid);
    event RequestFulfilled(bytes32 indexed requestId, string cid);
    event AccessGranted(string dataType, string lat, string lon, address indexed user);
    event AccessRevoked(string dataType, string lat, string lon, address indexed user);
    event CIDReturned(address indexed user, string dataType, string lat, string lon, string cid);

    modifier onlyAdmin() {
        require(msg.sender == admin, "Not admin");
        _;  
    }

    modifier canAccessLocation(string memory dataType, string memory lat, string memory lon) {
        bytes32 key = keccak256(abi.encodePacked(dataType, lat, lon));
        require(
            msg.sender == admin || locationAccess[key][msg.sender],
            "Not authorized for this location"
        );
        _;
    }

    constructor(address router, address _admin, string memory _apiBaseUrl) FunctionsClient(router) {
        admin = _admin;
        apiBaseUrl = _apiBaseUrl;
    }

    function grantAccess(string calldata dataType, string calldata lat, string calldata lon, address user) external onlyAdmin {
        bytes32 key = keccak256(abi.encodePacked(dataType, lat, lon));
        locationAccess[key][user] = true;
        emit AccessGranted(dataType, lat, lon, user);
    }

    function revokeAccess(string calldata dataType, string calldata lat, string calldata lon, address user) external onlyAdmin {
        bytes32 key = keccak256(abi.encodePacked(dataType, lat, lon));
        locationAccess[key][user] = false;
        emit AccessRevoked(dataType, lat, lon, user);
    }

    function setApiBaseUrl(string calldata _apiBaseUrl) external onlyAdmin {
        apiBaseUrl = _apiBaseUrl;
    }

    function requestCIDUpdate(string calldata dataType, string calldata lat, string calldata lon) external canAccessLocation(dataType, lat, lon) {
        _initiateRequestWithService(dataType, lat, lon, "", "", "");
    }

    function requestWeatherCID(string calldata dataType, string calldata lat, string calldata lon, string calldata service) external payable {
        require(msg.value >= requestFee, "Insufficient payment");
        _initiateRequestWithService(dataType, lat, lon, service, "", "");
    }

    function requestHistoricalWeatherCID(string calldata lat, string calldata lon, string calldata service, string calldata startDate, string calldata endDate) external payable {
        require(msg.value >= requestFee, "Insufficient payment");
        _initiateRequestWithService("historical", lat, lon, service, startDate, endDate);
    }

    function _initiateRequestWithService(string memory dataType, string memory lat, string memory lon, string memory service, string memory startDate, string memory endDate) internal {
        // Generate unique job run ID
        string memory jobRunId = string(abi.encodePacked("job_", block.timestamp, "_", block.number));
        
        string memory source = string(
            abi.encodePacked(
                "const dataType = args[0];\n",
                "const lat = parseFloat(args[1]);\n",
                "const lon = parseFloat(args[2]);\n",
                "const service = args[3];\n",
                "const startDate = args[4];\n",
                "const endDate = args[5];\n",
                "const jobRunId = args[6];\n",
                "const apiBaseUrl = args[7];\n",

                "let url = '';\n",
                "if (dataType === 'current') { url = apiBaseUrl; }\n",
                "else if (dataType === 'forecast') { url = apiBaseUrl + '/forecasts'; }\n",
                "else if (dataType === 'historical') { url = apiBaseUrl + '/historical'; }\n",

                "let requestData = {\n",
                "  id: jobRunId,\n",
                "  data: {\n",
                "    lat: lat,\n",
                "    lon: lon,\n",
                "    service: service\n",
                "  }\n",
                "};\n",

                "if (dataType === 'historical' && (startDate || endDate)) {\n",
                "  if (startDate) requestData.data.start_date = startDate;\n",
                "  if (endDate) requestData.data.end_date = endDate;\n",
                "}\n",

                "const response = await Functions.makeHttpRequest({\n",
                "  url,\n",
                "  method: 'POST',\n",
                "  headers: { 'x-api-key': secrets.apiKey, 'Content-Type': 'application/json' },\n",
                "  data: requestData\n",
                "});\n",

                "if (!response || response.error) throw Error('API call failed');\n",
                "return Functions.encodeString(response.data.cid);"
            )
        );

        string[] memory args = new string[](8);
        args[0] = dataType;
        args[1] = lat;
        args[2] = lon;
        args[3] = service;
        args[4] = startDate;
        args[5] = endDate;
        args[6] = jobRunId;
        args[7] = apiBaseUrl;

        FunctionsRequest.Request memory req;
        req.initializeRequestForInlineJavaScript(source);
        req.setArgs(args);

        uint64 subscriptionId = 344; // Your Chainlink Functions subscription ID
        uint32 gasLimit = 300000;
        bytes32 donID = 0x66756e2d626173652d7365706f6c69612d310000000000000000000000000000; // Base Sepolia DON ID

        bytes32 requestId = _sendRequest(req.encodeCBOR(), subscriptionId, gasLimit, donID);

        bytes32 key = keccak256(abi.encodePacked(dataType, lat, lon));
        requestIdToKey[requestId] = key;
        requestInitiator[requestId] = msg.sender;

        // RequestSent event is automatically emitted by FunctionsClient._sendRequest()
    }

    function fulfillRequest(bytes32 requestId, bytes memory response, bytes memory err) internal override {
        if (err.length > 0) revert(string(err));

        string memory cid = string(response);
        bytes32 key = requestIdToKey[requestId];
        address user = requestInitiator[requestId];

        if (user == admin || locationAccess[key][user]) {
            cidHistory[key].push(cid);
            latestCID[key] = cid;
            emit RequestFulfilled(requestId, cid);
        } else {
            userCIDs[user][key].push(cid);
            emit CIDReturned(user, "", "", "", cid);
        }
    }

    function getLatestCID(string calldata dataType, string calldata lat, string calldata lon)
        external
        view
        onlyAdmin
        returns (string memory)
    {
        return latestCID[keccak256(abi.encodePacked(dataType, lat, lon))];
    }

    function getCIDHistory(string calldata dataType, string calldata lat, string calldata lon)
        external
        view
        onlyAdmin
        returns (string[] memory)
    {
        return cidHistory[keccak256(abi.encodePacked(dataType, lat, lon))];
    }

    function getMyCIDs(string calldata dataType, string calldata lat, string calldata lon)
        external
        view
        returns (string[] memory)
    {
        bytes32 key = keccak256(abi.encodePacked(dataType, lat, lon));
        return userCIDs[msg.sender][key];
    }

    function getMyLatestCID(string calldata dataType, string calldata lat, string calldata lon)
        external
        view
        returns (string memory)
    {
        bytes32 key = keccak256(abi.encodePacked(dataType, lat, lon));
        string[] memory myCIDs = userCIDs[msg.sender][key];
        require(myCIDs.length > 0, "No CIDs found for this location");
        return myCIDs[myCIDs.length - 1]; // Return the latest (last) CID
    }
}