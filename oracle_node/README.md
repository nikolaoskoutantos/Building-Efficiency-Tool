## What is the Oracle Node?

**Requirements for a functional node:**

- A Postgres database to store node data and job information.
- The Chainlink core component, which by default includes a web application (GUI) for managing and monitoring the node.

The Chainlink oracle node acts as a bridge between smart contracts and real-world data or computation. It listens for on-chain requests and fulfills them by fetching, processing, or verifying data from off-chain sources, then returning the result to the blockchain.

**What to expect:**

- The node will receive requests from your smart contracts (e.g., for cost calculations or data retrieval).
- It will process these requests, interact with external APIs or services as needed, and return a result (such as a CID pointing to encrypted data on IPFS) back to the contract.
- This enables your contracts to access secure, tamper-proof, and up-to-date information that is not natively available on-chain.

## 1) Running the Postgres Database as the [official docs](https://docs.chain.link/chainlink-nodes/v1/running-a-chainlink-node) depicts

```
docker run --name cl-postgres -e POSTGRES_PASSWORD=mysecretpassword -p 5432:5432 -d postgres
```

## 2) Run the Chainlink Node

### Define the configuration files, like the [`chainlink-sepolia`](../chainlink-sepolia/) folder

### Windows Shell

```
$absolutePath = (Resolve-Path ../chainlink-sepolia).Path
docker run --platform linux/x86_64/v8 --name chainlink -v "${absolutePath}:/chainlink" -it -p 6688:6688 --add-host=host.docker.internal:host-gateway smartcontract/chainlink:2.17.0 node -config /chainlink/config.toml -secrets /chainlink/secrets.toml start -a /chainlink/.api
```
