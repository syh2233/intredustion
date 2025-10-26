# Quick test for Mosquitto connection
Write-Host "Quick Mosquitto Connection Test" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green

Set-Location $PSScriptRoot

# Test 1: Check if Mosquitto is running
Write-Host "1. Checking if Mosquitto is running..." -ForegroundColor Yellow
$mosquittoProcess = Get-Process | Where-Object {$_.Name -like "*mosquitto*"}
if ($mosquittoProcess) {
    Write-Host "✓ Mosquitto is running (PID: $($mosquittoProcess.Id))" -ForegroundColor Green
} else {
    Write-Host "✗ Mosquitto is not running" -ForegroundColor Red
    Write-Host "Please start Mosquitto first using:" -ForegroundColor Yellow
    Write-Host ".\start_mosquitto.ps1" -ForegroundColor Cyan
    exit
}

# Test 2: Check port listening
Write-Host "`n2. Checking port 1883..." -ForegroundColor Yellow
$portListener = netstat -an | findstr ":1883"
if ($portListener) {
    Write-Host "✓ Port 1883 is listening" -ForegroundColor Green
    Write-Host $portListener
} else {
    Write-Host "✗ Port 1883 is not listening" -ForegroundColor Red
}

# Test 3: Test basic connection
Write-Host "`n3. Testing basic connection..." -ForegroundColor Yellow
try {
    # Test publishing a message
    $result = & ".\mosquitto_pub.exe" -h 192.168.24.23 -t test/quick -m "Quick test message" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Successfully published test message" -ForegroundColor Green
    } else {
        Write-Host "✗ Failed to publish message" -ForegroundColor Red
        Write-Host "Error: $result" -ForegroundColor Red
    }
} catch {
    Write-Host "✗ Exception occurred: $_" -ForegroundColor Red
}

# Test 4: Test subscription
Write-Host "`n4. Testing ESP32 topics..." -ForegroundColor Yellow
try {
    $esp32Test = & ".\mosquitto_pub.exe" -h 192.168.24.23 -t "esp32/fire_alarm/data" -m '{"device_id":"test","temperature":25.0,"humidity":60.0,"flame":1500,"smoke":500}' 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Successfully published ESP32 test message" -ForegroundColor Green
    } else {
        Write-Host "✗ Failed to publish ESP32 message" -ForegroundColor Red
        Write-Host "Error: $esp32Test" -ForegroundColor Red
    }
} catch {
    Write-Host "✗ Exception occurred: $_" -ForegroundColor Red
}

Write-Host "`n=================================" -ForegroundColor Green
Write-Host "Test completed!" -ForegroundColor Green
Write-Host "`nTo monitor ESP32 data, run:" -ForegroundColor Cyan
Write-Host "mosquitto_sub.exe -h 192.168.24.23 -t `"esp32/#`" -v" -ForegroundColor Cyan
Write-Host "`nTo start Mosquitto, run:" -ForegroundColor Cyan
Write-Host ".\start_mosquitto.ps1" -ForegroundColor Cyan
Write-Host ""
Read-Host "Press Enter to exit"