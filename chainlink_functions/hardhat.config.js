require("dotenv").config();
require("@nomicfoundation/hardhat-toolbox");
require("hardhat-contract-sizer");
require("./tasks");
const { networks } = require("./networks");

const REPORT_GAS = process.env.REPORT_GAS?.toLowerCase() === "true";
const SOLC_SETTINGS = {
  optimizer: {
    enabled: true,
    runs: 1000,
  },
};

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  defaultNetwork: "baseSepolia",
  solidity: {
    compilers: [
      { version: "0.8.19", settings: SOLC_SETTINGS },
      { version: "0.8.7", settings: SOLC_SETTINGS },
      { version: "0.7.0", settings: SOLC_SETTINGS },
      { version: "0.6.6", settings: SOLC_SETTINGS },
      { version: "0.4.24", settings: SOLC_SETTINGS },
    ],
  },
  networks: {
    ...networks,
  },
  etherscan: {
    apiKey: {
      baseSepolia: process.env.BLOCKSCOUT_BASE_SEPOLIA_KEY, // <- from .env
    },
    customChains: [
      {
        network: "baseSepolia",
        chainId: 84532,
        urls: {
          apiURL: "https://base-sepolia.blockscout.com/api",
          browserURL: "https://base-sepolia.blockscout.com",
        },
      },
    ],
  },
  gasReporter: {
    enabled: REPORT_GAS,
    currency: "USD",
    outputFile: "gas-report.txt",
    noColors: true,
  },
  contractSizer: {
    runOnCompile: false,
    only: [
      "FunctionsConsumer",
      "AutomatedFunctionsConsumer",
      "FunctionsBillingRegistry"
    ],
  },
  paths: {
    sources: "./contracts",
    tests: "./test",
    cache: "./build/cache",
    artifacts: "./build/artifacts",
  },
  mocha: {
    timeout: 200000,
  },
};
