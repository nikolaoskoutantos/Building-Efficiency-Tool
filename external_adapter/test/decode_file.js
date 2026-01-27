/**
 * Decode base64 file content from decrypt response
 * Usage: node test/decode_file.js <base64_content> <output_filename>
 * 
 * Or programmatically:
 * const decodeAndSave = require('./test/decode_file');
 * decodeAndSave(base64String, 'output.xlsx');
 */

const fs = require('fs');
const path = require('path');

/**
 * Decode base64 content and save to file
 * @param {string} base64Content - Base64 encoded file content
 * @param {string} outputFilename - Output filename (default: decoded_file.xlsx)
 */
function decodeAndSave(base64Content, outputFilename = 'decoded_file.xlsx') {
  try {
    // Decode base64
    const buffer = Buffer.from(base64Content, 'base64');
    
    // Determine output path
    const outputPath = path.resolve(__dirname, outputFilename);
    
    // Write to file
    fs.writeFileSync(outputPath, buffer);
    
    console.log(`✅ File decoded and saved to: ${outputPath}`);
    console.log(`📊 File size: ${buffer.length} bytes`);
    
    return outputPath;
  } catch (error) {
    console.error('❌ Error decoding file:', error.message);
    throw error;
  }
}

// CLI usage
if (require.main === module) {
  const args = process.argv.slice(2);
  
  if (args.length === 0) {
    console.log('Usage: node decode_file.js <base64_content> [output_filename]');
    console.log('\nExample:');
    console.log('  node decode_file.js "UEsDBBQAAA..." decrypted.xlsx');
    process.exit(1);
  }
  
  const base64Content = args[0];
  const outputFilename = args[1] || 'decoded_file.xlsx';
  
  decodeAndSave(base64Content, outputFilename);
}

module.exports = decodeAndSave;
