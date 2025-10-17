// SPDX-License-Identifier: MIT
pragma solidity ^0.8.7;

import {Chainlink, ChainlinkClient} from "@chainlink/contracts/src/v0.8/operatorforwarder/ChainlinkClient.sol";
import {ConfirmedOwner} from "@chainlink/contracts/src/v0.8/shared/access/ConfirmedOwner.sol";
import "https://github.com/OpenZeppelin/openzeppelin-contracts/blob/v4.9.6/contracts/access/Ownable.sol";
import {LinkTokenInterface} from "@chainlink/contracts/src/v0.8/interfaces/LinkTokenInterface.sol"; // <-- Add this

contract CIDRequester is ChainlinkClient, Ownable {
    using Chainlink for Chainlink.Request;

    // ---- Chainlink config ----
    address public operator;
    bytes32 public jobId;
    uint256 public feeJuels;

    // ---- Result storage ----
    string public latestCID;
    bytes32 public latestRequestId;

    event Requested(bytes32 indexed requestId, string lat, string lon, string service);
    event Fulfilled(bytes32 indexed requestId, string cid);

    // 👇 Ownable(msg.sender) required for OpenZeppelin v5
    constructor(
        address _linkToken,
        address _operator,
        bytes32 _jobId,
        uint256 _feeJuels
    ) {
        _setChainlinkToken(_linkToken);
        _setChainlinkOracle(_operator);
        operator = _operator;
        jobId = _jobId;
        feeJuels = _feeJuels;
    }

    // ---- Admin tweaks ----
    function setOperator(address _op) external onlyOwner {
        operator = _op;
        _setChainlinkOracle(_op);
    }

    function setJobId(bytes32 _jobId) external onlyOwner {
        jobId = _jobId;
    }

    function setFeeJuels(uint256 _feeJuels) external onlyOwner {
        feeJuels = _feeJuels;
    }

    // ---- Make a request ----
    function requestCID(
        string calldata lat,
        string calldata lon,
        string calldata service
    ) external returns (bytes32 reqId) {
        require(jobId != 0x0, "jobId not set");
        require(operator != address(0), "operator not set");

        require(
            LinkTokenInterface(_chainlinkTokenAddress()).balanceOf(address(this)) >= feeJuels,
            "Insufficient LINK"
        );

        Chainlink.Request memory req = _buildChainlinkRequest(
            jobId,
            address(this),
            this.fulfillBytes.selector
        );

        // Build JSON body
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

        // Explicitly call Chainlink library functions
        Chainlink._add(req, "requestData", body);
        Chainlink._add(req, "path", "cid");

        reqId = _sendChainlinkRequestTo(operator, req, feeJuels);
        latestRequestId = reqId;
        emit Requested(reqId, lat, lon, service);
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

    // Withdraw LINK
    function withdrawLink(address to, uint256 amount) external onlyOwner {
        require(to != address(0), "to=0");
        require(
            LinkTokenInterface(_chainlinkTokenAddress()).balanceOf(address(this)) >= amount,
            "Insufficient LINK balance"
        );
        require(
            LinkTokenInterface(_chainlinkTokenAddress()).transfer(to, amount),
            "LINK transfer failed"
        );
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
