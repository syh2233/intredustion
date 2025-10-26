# Simple localhost test
Write-Host "Testing Localhost Connection" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green

Set-Location $PSScriptRoot

# Test localhost specifically
Write-Host "Testing localhost (127.0.0.1)..." -ForegroundColor Yellow

try {
    # Test publishing
    Write-Host "Publishing test message..." -ForegroundColor Cyan
    $result = & ".\mosquitto_pub.exe" -h 127.0.0.1 -t test/local -m "Localhost test" 2>&1

    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Successfully published to localhost" -ForegroundColor Green

        # Test subscription
        Write-Host "Testing subscription..." -ForegroundColor Cyan
        $job = Start-Job -ScriptBlock {
            cd $args[0]
            & ".\mosquitto_sub.exe" -h 127.0.0.1 -t test/sub -t 1 -v
        } -ArgumentList $PSScriptRoot

        Start-Sleep -Seconds 1

        $result = & ".\mosquitto_pub.exe" -h 127.0.0.1 -t test/sub -m "Subscription test"

        Start-Sleep -Seconds 2

        Stop-Job $job
        Remove-Job $job

        Write-Host "✓ Subscription test successful" -ForegroundColor Green

        # Test ESP32 topic
        Write-Host "Testing ESP32 topic..." -ForegroundColor Cyan
        $esp32Message = '{"device_id":"test","temperature":25.0,"humidity":60.0,"flame":1500,"smoke":500}'
        $result = & ".\mosquitto_pub.exe" -h 127.0.0.1 -t "esp32/fire_alarm/data" -m $esp32Message

        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ ESP32 topic test successful" -ForegroundColor Green
        } else {
            Write-Host "✗ ESP32 topic test failed" -ForegroundColor Red
        }

    } else {
        Write-Host "✗ Failed to publish to localhost" -ForegroundColor Red
        Write-Host "Error: $result" -ForegroundColor Red
    }
} catch {
    Write-Host "✗ Exception: $_" -ForegroundColor Red
}

Write-Host "`nRecommended ESP32 configuration:" -ForegroundColor Yellow
Write-Host 'MQTT_SERVERS = [' -ForegroundColor Cyan
Write-Host '    {"server": "127.0.0.1", "port": 1883, "name": "Local Mosquitto"},' -ForegroundColor White
Write-Host '    {"server": "test.mosquitto.org", "port": 1883, "name": "Public Mosquitto"}' -ForegroundColor White
Write-Host ']' -ForegroundColor Cyan

Write-Host "`n=================================" -ForegroundColor Green
Write-Host "Test completed!" -ForegroundColor Green
Write-Host ""
Read-Host "Press Enter to exit"