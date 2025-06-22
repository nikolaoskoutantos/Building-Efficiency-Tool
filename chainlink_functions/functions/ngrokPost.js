const service = args[0];
const lat = args[1];
const lon = args[2];

const url = "https://23b6-2a02-2149-8b5d-f00-a14e-2170-6067-190e.ngrok-free.app/";

const body = {
  id: "string",
  data: {
    service: service,
    lat: parseFloat(lat),
    lon: parseFloat(lon)
  }
};

const response = await Functions.makeHttpRequest({
  url: url,
  method: "POST",
  headers: {
    "Content-Type": "application/json"
  },
  data: body
});

if (response.error) {
  throw Error(`Request failed: ${response.error}`);
}

const cid = response.data?.cid;

if (!cid) {
  throw Error("No 'cid' found in the response.");
}

return Functions.encodeString(cid);
