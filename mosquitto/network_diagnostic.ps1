# Network diagnostic script for Mosquitto
Write-Host "Network Diagnostic for Mosquitto" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green

Set-Location $PSScriptRoot

# 1. Check current IP configuration
Write-Host "1. Current IP Configuration:" -ForegroundColor Yellow
$ipConfig = Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias (Get-NetAdapter | Where-Object {$_.Status -eq "Up"}).Name
$ipConfig | Format-Table IPAddress, InterfaceAlias, PrefixLength -AutoSize

# 2. Check which IP addresses we can use
Write-Host "`n2. Available IP Addresses for testing:" -ForegroundColor Yellow
$localIPs = @("127.0.0.1", "localhost")
$networkIPs = $ipConfig.IPAddress | Where-Object {$_ -notlike "127.*" -and $_ -notlike "169.*"}

Write-Host "Local loopback:" -ForegroundColor Cyan
foreach ($ip in $localIPs) {
    Write-Host "  - $ip"
}

Write-Host "Network interfaces:" -ForegroundColor Cyan
foreach ($ip in $networkIPs) {
    Write-Host "  - $ip"
}

# 3. Test different IP addresses
Write-Host "`n3. Testing different IP addresses:" -ForegroundColor Yellow

$testIPs = @("127.0.0.1", "localhost") + $networkIPs
$successfulIPs = @()

foreach ($testIP in $testIPs) {
    Write-Host "Testing $testIP..." -ForegroundColor Cyan
    try {
        $result = & ".\mosquitto_pub.exe" -h $testIP -t test/diag -m "test" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ SUCCESS" -ForegroundColor Green
            $successfulIPs += $testIP
        } else {
            Write-Host "  ✗ FAILED" -ForegroundColor Red
        }
    } catch {
        Write-Host "  ✗ EXCEPTION: $_" -ForegroundColor Red
    }
}

# 4. Test subscription
Write-Host "`n4. Testing subscription with successful IPs:" -ForegroundColor Yellow
foreach ($ip in $successfulIPs) {
    Write-Host "Testing subscription on $ip..." -ForegroundColor Cyan
    try {
        # Start a subscriber in background
        $subscriberJob = Start-Job -ScriptBlock {
            param($mosquittoPath, $ip)
            cd $mosquittoPath
            & ".\mosquitto_sub.exe" -h $ip -t test/sub -t 1 -v
        } -ArgumentList $PSScriptRoot, $ip

        # Wait a moment
        Start-Sleep -Seconds 1

        # Publish a message
        $result = & ".\mosquitto_pub.exe" -h $ip -t test/sub -m "Subscription test"

        # Wait for subscriber
        Start-Sleep -Seconds 2

        # Stop the job
        Stop-Job $subscriberJob
        Remove-Job $subscriberJob

        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ Subscription test successful" -ForegroundColor Green
        } else {
            Write-Host "  ✗ Subscription test failed" -ForegroundColor Red
        }
    } catch {
        Write-Host "  ✗ Subscription exception: $_" -ForegroundColor Red
    }
}

# 5. Update ESP32 configuration
Write-Host "`n5. Recommended ESP32 configuration:" -ForegroundColor Green
if ($successfulIPs.Count -gt 0) {
    Write-Host "MQTT_SERVERS = [" -ForegroundColor Cyan
    foreach ($ip in $successfulIPs) {
        if ($ip -eq "127.0.0.1" -or $ip -eq "localhost") {
            Write-Host '    {"server": "127.0.0.1", "port": 1883, "name": "Local Mosquitto"},' -ForegroundColor White
        } else {
            Write-Host "    {`"server`": `"$ip`", `"port`": 1883, `"name`": `"Network Mosquitto`"}," -ForegroundColor White
        }
    }
    Write-Host '    {"server": "test.mosquitto.org", "port": 1883, "name": "Public Mosquitto"}' -ForegroundColor White
    Write-Host "]" -ForegroundColor Cyan

    Write-Host "`nUpdate your ESP32 code with the successful IP addresses above." -ForegroundColor Yellow
} else {
    Write-Host "No successful IP addresses found. Check firewall and network configuration." -ForegroundColor Red
}

Write-Host "`n=================================" -ForegroundColor Green
Write-Host "Diagnostic completed!" -ForegroundColor Green
Write-Host ""
Read-Host "Press Enter to exit"