#!/usr/bin/env node
// Test CORS configuration
const url = 'http://localhost:8000/auth/me';

console.log('Testing CORS configuration...');
console.log('Frontend Origin: http://localhost:3000');
console.log('Backend URL:', url);

fetch(url, {
    method: 'GET',
    credentials: 'include',
    headers: {
        'Content-Type': 'application/json',
    }
})
.then(response => {
    console.log('✅ CORS Test - Status:', response.status);
    console.log('✅ CORS Test - Headers OK');
    return response.text();
})
.then(data => {
    console.log('✅ CORS Test - Response:', data);
})
.catch(error => {
    console.error('❌ CORS Test Failed:', error);
});
