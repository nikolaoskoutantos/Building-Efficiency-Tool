# QoE Application — Smart Contracts

This directory contains the Solidity smart contracts used in the QoE Application for secure, decentralized operations and integration with Chainlink oracles.

## Overview

The smart contracts in this folder enable on-chain management of data, requests, and cost calculations related to the QoE platform. They are designed to interact with Chainlink nodes and external adapters for reliable, tamper-proof automation and data exchange.

> **Note:** Each contract returns a CID (Content Identifier) as a pointer to encrypted data stored on IPFS, rather than storing off-chain data directly on-chain. This approach avoids excessive on-chain costs and allows users to access the data they have purchased securely and efficiently.

## Status

> ⚠️ **Pending Update for Documentation** - Contract documentation and deployment guides are currently being updated to reflect recent changes in the external adapter integration and Vault encryption workflow.

## Contracts

- `CostCIDRequest.sol`: Manages cost calculations and requests associated with CID operations, integrating with Chainlink for off-chain computation.
- `CIDRequester.sol`: Requests and stores IPFS CIDs via Chainlink; supports subscription and on-demand billing.
- `CID_Sub_Model.sol`: Requests and stores IPFS CIDs via Chainlink; supports subscription and on-demand billing.

> ⚠️ **Note:** Local editor errors (especially import issues) often do not appear in Remix IDE. Try compiling in Remix, most problems are resolved there automatically.

## Prerequisites

- Solidity compiler (version as specified in the contract)
- Hardhat or Truffle for deployment and testing
- Access to a Chainlink node for oracle operations

## Operator Contract Setup

To use this contract, you must have a Chainlink Operator (oracle) set up to fulfill requests. The Operator contract acts as the bridge between your smart contract and off-chain data/services.

For detailed instructions on setting up and running a Chainlink Operator, see the official documentation:

- [Chainlink: Fulfilling Requests](https://docs.chain.link/chainlink-nodes/v1/fulfilling-requests)

Ensure your Operator is properly configured and funded with LINK to process requests from your contract.

## Usage

This contract is intended to be deployed on EVM-compatible blockchains (e.g., Ethereum, Polygon). It is typically used in conjunction with Chainlink nodes and the external adapter provided in the `external_adapter/` directory.

## Constructor & Standard Values

When deploying these contracts, you will typically need to provide several standard parameters in the constructor. These are required for Chainlink oracle integration and contract operation:

- **Operator Address**: The address of the Chainlink Operator contract that will fulfill requests.
- **LINK Token Address**: The address of the LINK token contract (varies by network).
- **Oracle Fee (in Juels)**: The amount of LINK (in Juels, where 1 LINK = 10^18 Juels) required to pay for each oracle request.
- **Job ID (bytes32)**: The Chainlink job ID, provided as a bytes32 value (see below for format and conversion).

### Example Standard Values (Base Sepolia Testnet)

- Operator: `0x359EC6760d0e46C3d8dBc23835679b9875eDcbCF`
- LINK Token: `0xE4aB69C077896252FAFBD49EFD26B5D171A32410` (Base Sepolia)
- Fee: `100000000000000000` (0.1 LINK)
- Job ID (as bytes32): `0x123e4567e89b12d3a45642661417400000000000000000000000000000000000` (replace with your actual job ID, no hyphens, padded to 32 bytes)

> **Note:** The job ID must be provided as a `bytes32` value when instantiating the contract. To convert a job ID string (with hyphens removed) to `bytes32`, you can use web3 or Remix:

**Example (web3.js):**

```js
const jobIdString = '123e4567e89b12d3a456426614174000'; // no hyphens
const jobIdBytes32 = web3.utils.padRight('0x' + jobIdString, 66); // 66 chars for 0x + 64 hex digits
// Use jobIdBytes32 as the constructor argument
```

**Example (Remix):**

- In the Remix Deploy & Run module, enter the job ID as a hex string, padded to 32 bytes (64 hex characters, prefixed with 0x).

## Deployment

You can use [Remix IDE](https://remix.ethereum.org/) to compile, deploy, and interact with this contract directly from your browser. Remix is responsible for starting and managing the initial deployment process in general, making it easy to test and launch contracts without additional setup.

Deployment steps:

1. Open Remix and load the contract file.
2. Compile the contract using the Solidity compiler in Remix.
3. Deploy the contract to your chosen network (e.g., local, testnet, or mainnet) using the Remix Deploy & Run module.
4. After deployment, configure Chainlink jobs and external adapters as needed.
