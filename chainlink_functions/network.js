require("dotenv").config();

const getNetworks = () => {
  const privateKey = process.env.PRIVATE_KEY;

  if (!privateKey && process.env.SKIP_PRIVATE_KEY_CHECK !== "true") {
    throw new Error("Set the PRIVATE_KEY environment variable with your EVM wallet private key");
  }

  return {
    baseSepolia: {
      url: process.env.BASE_SEPOLIA_RPC_URL,
      chainId: 84532,
      accounts: privateKey ? [privateKey] : [],
      verifyApiKey: process.env.BLOCKSCOUT_BASE_SEPOLIA_KEY,
    },
  };
};

module.exports = {
  networks: getNetworks(),
};
