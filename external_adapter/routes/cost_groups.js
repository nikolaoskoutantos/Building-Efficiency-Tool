const express = require('express');
const router = express.Router();
const { handleCostGroupRequest } = require('../utils/costGroupProcessor');

/**
 * @swagger
 * /cost_groups:
 *   post:
 *     summary: Process cost data with grouping and filtering
 *     description: Apply cost grouping filters/transformations to cost data files, encrypt the result (if Vault enabled), and upload to IPFS. Returns the IPFS CID for cost analysis.
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - id
 *               - data
 *             properties:
 *               id:
 *                 type: string
 *                 description: Job Run ID
 *               data:
 *                 type: object
 *                 required:
 *                   - query_type
 *                 properties:
 *                   query_type:
 *                     type: string
 *                     description: Type of cost analysis to apply to the Proforma.xlsx file
 *                     enum: [filter, transform, search, extract, aggregate]                   product_type:
                     type: string
                     description: Product type to filter costs for
                     enum: [product1, product2, product3, product4, product5, hvac_system, lighting_system, electrical_system, plumbing_system, building_envelope]                   query_params:
                     type: object
                     description: Cost grouping parameters specific to the query_type
 *                     properties:
 *                       filters:
 *                         type: array
 *                         description: Array of cost filter conditions
 *                         items:
 *                           type: object
 *                           properties:
 *                             field:
 *                               type: string
 *                               description: Cost field to filter on (e.g., category, amount, type)
 *                             operator:
 *                               type: string
 *                               enum: [eq, ne, gt, lt, gte, lte, contains, regex]
 *                             value:
 *                               type: string
 *                       transforms:
 *                         type: array
 *                         description: Array of cost data transformations
 *                         items:
 *                           type: object
 *                           properties:
 *                             operation:
 *                               type: string
 *                               enum: [select, rename, calculate, group, sort]
 *                             params:
 *                               type: object
 *                       search_terms:
 *                         type: array
 *                         description: Cost terms to search for
 *                         items:
 *                           type: string
 *                       extract_pattern:
 *                         type: string
 *                         description: Regex pattern for data extraction
 *                       aggregations:
 *                         type: array
 *                         description: Aggregation operations
 *                         items:
 *                           type: object
 *                           properties:
 *                             field:
 *                               type: string
 *                             operation:
 *                               type: string
 *                               enum: [sum, avg, count, min, max]
 *                   output_format:
 *                     type: string
 *                     description: Desired output format
                     enum: [json, csv, excel, xlsx, xml, txt]
 *                     default: json
 *     responses:
 *       200:
 *         description: File processed successfully and uploaded to IPFS
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 jobRunID:
 *                   type: string
 *                 data:
 *                   type: object
 *                   properties:
 *                     cid:
 *                       type: string
 *                     query_type:
 *                       type: string
 *                     processed_records:
 *                       type: number
 *                     output_size:
 *                       type: number
 *                 result:
 *                   type: string
 *                 statusCode:
 *                   type: number
 *       400:
 *         description: Bad request due to missing or invalid parameters
 *       500:
 *         description: Error processing query or uploading to IPFS
 */
router.post('/', (req, res) => handleCostGroupRequest(req, res));

module.exports = router;