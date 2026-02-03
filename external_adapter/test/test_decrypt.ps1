# Test script to decrypt and download Excel file from IPFS
# Usage: .\test\test_decrypt.ps1

Write-Host "🔓 Testing decrypt endpoint..." -ForegroundColor Cyan

# API configuration
$API_URL = "http://localhost:3001/decrypt"
$API_KEY = "123123sdasd124qsfhfgnczXC2345234143afh4214"
$CID = "QmPPs2h1qvFSrVDfAK1vSaNPxZvZf7S47HshtsysTuEXVw"


# Request body
$body = @{
    cid = $CID
} | ConvertTo-Json

# Headers
$headers = @{
    "accept" = "application/json"
    "x-api-key" = $API_KEY
    "Content-Type" = "application/json"
}

try {
    Write-Host "📡 Sending decrypt request for CID: $CID" -ForegroundColor Yellow
    
    # Make the request
    $response = Invoke-RestMethod -Uri $API_URL -Method Post -Headers $headers -Body $body
    
    Write-Host "✅ Decrypt request successful!" -ForegroundColor Green
    Write-Host "📄 Filename: $($response.data.filename)" -ForegroundColor Cyan
    Write-Host "🔐 Algorithm: $($response.metadata.algorithm)" -ForegroundColor Cyan
    Write-Host "📊 Data type: $($response.metadata.data_type)" -ForegroundColor Cyan
    
    # Extract base64 content
    $base64Content = $response.data.content_base64
    
    if ([string]::IsNullOrEmpty($base64Content)) {
        Write-Host "❌ No content_base64 found in response!" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "🔄 Decoding base64 content..." -ForegroundColor Yellow
    
    # Decode base64 to bytes
    $bytes = [Convert]::FromBase64String($base64Content)
    
    # Determine output filename
    $outputFilename = $response.data.filename
    if ([string]::IsNullOrEmpty($outputFilename)) {
        $outputFilename = "decrypted_file_$(Get-Date -Format 'yyyyMMdd_HHmmss').xlsx"
    }
    
    $outputPath = Join-Path $PSScriptRoot $outputFilename
    
    # Write bytes to file
    [System.IO.File]::WriteAllBytes($outputPath, $bytes)
    
    Write-Host "✅ File saved successfully!" -ForegroundColor Green
    Write-Host "📁 Location: $outputPath" -ForegroundColor Cyan
    Write-Host "📊 Size: $($bytes.Length) bytes" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "🎉 You can now open the file in Excel!" -ForegroundColor Green
    Write-Host "   Start-Process `"$outputPath`"" -ForegroundColor Gray
    
    # Ask if user wants to open the file
    $openFile = Read-Host "Do you want to open the file now? (Y/N)"
    if ($openFile -eq "Y" -or $openFile -eq "y") {
        Start-Process $outputPath
    }
    
} catch {
    Write-Host "❌ Error occurred:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    
    if ($_.ErrorDetails.Message) {
        Write-Host "Response details:" -ForegroundColor Yellow
        Write-Host $_.ErrorDetails.Message -ForegroundColor Red
    }
    
    exit 1
}
