const { createRequest } = require('../index.js');

const input = {
  id: '1',
  data: {
    lat: '37.178055',
    lon: '-3.600833',
  },
};

createRequest(input, (statusCode, data) => {
  console.log('Status Code:', statusCode);
  console.log('Data:', JSON.stringify(data, null, 2));
});
