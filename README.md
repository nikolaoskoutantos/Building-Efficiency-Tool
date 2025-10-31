# Building Efficiency Tool Application

![Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python) ![JavaScript](https://img.shields.io/badge/javascript-ES2021-yellow?logo=javascript) ![Solidity](https://img.shields.io/badge/solidity-%5E0.8.20-black?logo=solidity) ![Vue.js](https://img.shields.io/badge/vue-3.x-brightgreen?logo=vue.js) ![Docker](https://img.shields.io/badge/docker-ready-blue?logo=docker) ![IPFS](https://img.shields.io/badge/IPFS-enabled-blueviolet?logo=ipfs) ![Caddy](https://img.shields.io/badge/Caddy-proxy-green?logo=caddy) ![Vault](https://img.shields.io/badge/Vault-secrets-yellow?logo=hashicorp) [![Build Status](https://github.com/nikolaoskoutantos/QOE-Application-Chainlink-DKG-intergration/actions/workflows/ci.yml/badge.svg)](https://github.com/nikolaoskoutantos/QOE-Application-Chainlink-DKG-intergration/actions/workflows/ci.yml) ![License](https://img.shields.io/github/license/nikolaoskoutantos/QOE-Application-Chainlink-DKG-intergration) ![Issues](https://img.shields.io/github/issues/nikolaoskoutantos/QOE-Application-Chainlink-DKG-intergration) ![Last Commit](https://img.shields.io/github/last-commit/nikolaoskoutantos/QOE-Application-Chainlink-DKG-intergration)

## Introduction

QoE Application is a modular, end-to-end platform for optimizing HVAC energy consumption and integrating off-chain data with smart contracts. It leverages Chainlink oracles, IPFS for decentralized storage, and a secure FastAPI backend with machine learning for real-time predictions and optimization. The system is designed for research and production use in energy management, providing:

- **Automated HVAC optimization** using scikit-learn models trained on sensor and weather data
- **Chainlink external adapter** for secure, verifiable off-chain data delivery to smart contracts
- **Decentralized storage** of results and knowledge assets via IPFS
- **Secure proxying and secrets management** with Caddy and Vault
- **Modular architecture** with Docker Compose for easy deployment and scaling

The repository is organized into clearly separated modules for backend (FastAPI), frontend (Vue.js), smart contracts (Solidity), Chainlink adapters (Node.js), and supporting infrastructure (logger, data, oracle node). Each module can be developed, tested, and deployed independently, while working together to deliver a robust, research-grade solution for energy and quality-of-experience optimization.

## Services Overview

| Folder                                | Service/Module             | Description                                                                                  |
| :---------------------------------------------- | :------------------------- | :------------------------------------------------------------------------------------------- |
| [`api/`](./api/)                                 | Backend API                | FastAPI backend for REST endpoints, ML, DB access, and HVAC optimization logic.              |
| [`ui/`](./ui/)                                   | Frontend UI                | Vue.js web application for user interaction and visualization.                               |
| [`external_adapter/`](./external_adapter/)       | Chainlink Adapter          | Node.js service for Chainlink node integration, weather fetch, and IPFS CID return.          |
| [`chainlink/`](./chainlink/)                     | Chainlink Node Config      | Chainlink node scripts, job specs, and smart contract interaction helpers.                   |
| [`smart_contracts/`](./smart_contracts/)         | Smart Contracts            | Solidity contracts for on-chain logic, CID requests, and energy incentives.                  |
| [`data_infrastructure/`](./data_infrastructure/) | Data Infrastructure        | Docker Compose, Vault, and IPFS setup for secure, decentralized data and secrets management. |
| [`logger/`](./logger/)                           | Logging & Monitoring       | Caddy, Loki, Grafana, and Promtail for logging, metrics, and monitoring.                     |
| [`oracle_node/`](./oracle_node/)                 | Oracle Node Infrastructure | Chainlink node deployment and configuration for oracle operations.                           |
| [`notebooks/`](./notebooks/)                     | Research Notebooks         | Jupyter notebooks for validation, prototyping, and data exploration.                         |
| [`drafts/`](./drafts/)                           | Drafts & Experiments       | Experimental code, drafts, and early-stage prototypes.                                       |
| [`saved_models/`](./api/saved_models/)           | ML Model Artifacts         | Trained scikit-learn models and artifacts for HVAC optimization.                             |

> **Note:** Each folder contains its own README and setup instructions where applicable.

## Demo Deployment (with Custom DNS)

Below are the current and planned DNS assignments for the demo deployment. Some services are not yet deployed and will be available soon.

| Service                | DNS Name / URL                        | Status / Notes                                   |
|------------------------|---------------------------------------|--------------------------------------------------|
| Backend API            | _Not yet deployed_                    | FastAPI backend (planned)                        |
| Frontend UI            | _Not yet deployed_                    | Vue.js web interface (planned)                   |
| Chainlink Adapter      | [adapter.nkoutantos.com/api-docs](https://adapter.nkoutantos.com/api-docs) | Swagger UI for external adapter (active)         |
| Oracle Node            | [oracle.nkoutantos.com](https://oracle.nkoutantos.com)         | Oracle node management (active)                  |
| Logger/Grafana         | [grafana.nkoutantos.com](https://grafana.nkoutantos.com)       | Grafana dashboards and metrics (active)          |
| Logger/Loki            | _Runs locally_                        | Loki log aggregation (local only)                |
| Vault                  | [vault.nkoutantos.com](https://vault.nkoutantos.com)           | HashiCorp Vault UI/API (active)                  |
| IPFS Gateway           | [ipfs.nkoutantos.com](https://ipfs.nkoutantos.com)             | IPFS HTTP gateway (active)                       |
| Portainer              | [portainer.nkoutantos.com](https://portainer.nkoutantos.com)   | Docker container management UI (active)          |

> **Tip:** Update your DNS provider to point these subdomains to your server's public IP. Configure your reverse proxy (Caddy, Nginx, etc.) to route each subdomain to the correct Docker service/container.
