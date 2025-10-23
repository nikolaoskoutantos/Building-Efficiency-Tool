const app = require('./app');

const port = process.env.PORT || 8080;
app.listen(port, '0.0.0.0', () => {
  console.log(`Server is listening on port ${port}`);
  console.log(`Swagger docs available at http://localhost:${port}/api-docs`);
});
