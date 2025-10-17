const { simulateScript } = require("@chainlink/functions-toolkit");
const path = require("path");
const fs = require("fs");

const scriptPath = path.resolve(__dirname, "./functions/ngrokPost.js");

// Confirm the path exists
if (!fs.existsSync(scriptPath)) {
  console.error("❌ Script not found at:", scriptPath);
  process.exit(1);
}

console.log("✅ Found script at:", scriptPath);

(async () => {
  try {
    const result = await simulateScript({
      source: scriptPath,
      args: ["", "48.2", "16.3"]
    });
    console.log("✅ Simulation result:", result);
  } catch (error) {
    console.error("❌ Simulation error:", error.message || error);
  }
})();
