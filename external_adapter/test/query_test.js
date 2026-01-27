const request = require('supertest');
const app = require('../app');

describe('Query Controller', () => {
  const validApiKey = process.env.API_KEY || 'test-key';

  describe('POST /query', () => {
    it('should process filter query successfully', async () => {
      const testData = Buffer.from(JSON.stringify([
        {"name": "John", "age": 30, "city": "NYC"},
        {"name": "Jane", "age": 25, "city": "LA"}
      ])).toString('base64');

      const response = await request(app)
        .post('/query')
        .set('x-api-key', validApiKey)
        .send({
          id: 'test-filter-001',
          data: {
            query_type: 'filter',
            file_source: 'data',
            file_data: testData,
            query_params: {
              filters: [
                { field: 'age', operator: 'gte', value: '30' }
              ]
            },
            output_format: 'json'
          }
        });

      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('jobRunID', 'test-filter-001');
      expect(response.body).toHaveProperty('data');
      expect(response.body.data).toHaveProperty('cid');
      expect(response.body.data).toHaveProperty('processed_records', 1);
    });

    it('should process search query successfully', async () => {
      const testData = Buffer.from('This is a test file with some content').toString('base64');

      const response = await request(app)
        .post('/query')
        .set('x-api-key', validApiKey)
        .send({
          id: 'test-search-001',
          data: {
            query_type: 'search',
            file_source: 'data',
            file_data: testData,
            query_params: {
              search_terms: ['test', 'content']
            },
            output_format: 'json'
          }
        });

      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('jobRunID', 'test-search-001');
      expect(response.body.data).toHaveProperty('processed_records');
    });

    it('should process extract query successfully', async () => {
      const testData = Buffer.from('Contact: john@example.com or jane@test.org').toString('base64');

      const response = await request(app)
        .post('/query')
        .set('x-api-key', validApiKey)
        .send({
          id: 'test-extract-001',
          data: {
            query_type: 'extract',
            file_source: 'data',
            file_data: testData,
            query_params: {
              extract_pattern: '\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b'
            },
            output_format: 'json'
          }
        });

      expect(response.status).toBe(200);
      expect(response.body.data).toHaveProperty('processed_records', 2);
    });

    it('should return 400 for missing required parameters', async () => {
      const response = await request(app)
        .post('/query')
        .set('x-api-key', validApiKey)
        .send({
          id: 'test-error-001',
          data: {
            // missing query_type and file_source
          }
        });

      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('error');
    });

    it('should return 401 for missing API key', async () => {
      const response = await request(app)
        .post('/query')
        .send({
          id: 'test-auth-001',
          data: {
            query_type: 'filter',
            file_source: 'data'
          }
        });

      expect(response.status).toBe(401);
    });
  });
});