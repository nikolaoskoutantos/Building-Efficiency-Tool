# Project Structure Overview

This repository is organized into three main components:

## 1. Chainlink Functions

- **Location:** `chainlink_functions/`
- **Purpose:** Handles the logic and smart contracts for integrating with 3rd party services using Chainlink Functions.
- **Details:**
  - Contains Solidity smart contracts and scripts for deploying and interacting with them.
  - Enables secure, decentralized connections between the blockchain and external APIs or data sources.

## 2. UI (Vue.js Application)

- **Location:** `ui/`
- **Purpose:** The frontend of the application, built with Vue.js.
- **Details:**
  - Provides a modern, user-friendly interface for interacting with the system.
  - Communicates with the backend API to display data and trigger actions.

## 3. API (FastAPI Backend)

- **Location:** `api/`
- **Purpose:** The backend of the application, built with FastAPI.
- **Details:**
  - Exposes RESTful endpoints for the UI and other clients.
  - Handles authentication, business logic, and database operations.
  - Can interact with smart contracts and external services as needed.

---

**Summary:**

- `chainlink_functions/` manages smart contract logic and 3rd party integrations.
- `ui/` is the Vue.js frontend.
- `api/` is the FastAPI backend.

Each part is modular, making the system flexible and easy to maintain.
