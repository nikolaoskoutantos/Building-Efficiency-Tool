const fs = require("fs");
const { Location, ReturnType, CodeLanguage } = require("@chainlink/functions-toolkit");

// Configure the request for your HTTP API
const requestConfig = {
  // Path to your actual HTTP POST script
  source: fs.readFileSync("./functions/ngrokPost.js").toString(),

  // Script location type
  codeLocation: Location.Inline,

  // You don't need secrets unless you're using an API key
  secrets: {},

  // Location of secrets (not used in this case, still required)
  secretsLocation: Location.DONHosted,

  // Arguments passed to the script: [service, lat, lon]
  args: ["", "48.2", "16.3"],

  // Code type
  codeLanguage: CodeLanguage.JavaScript,

  // What kind of data do you expect to be returned from the HTTP POST?
  expectedReturnType: ReturnType.string,
};

module.exports = requestConfig;
