# Quick IP Check
Write-Host "Quick IP Address Check" -ForegroundColor Green
Write-Host "=====================" -ForegroundColor Green

# Get IP configuration
$ipConfig = Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias (Get-NetAdapter | Where-Object {$_.Status -eq "Up"}).Name
Write-Host "Computer IP Addresses:" -ForegroundColor Yellow
$ipConfig | Format-Table IPAddress, InterfaceAlias, PrefixLength -AutoSize

# Check if any IP matches ESP32
$esp32IP = "192.168.24.23"
$matchingIPs = $ipConfig | Where-Object {$_.IPAddress -eq $esp32IP}

if ($matchingIPs) {
    Write-Host "`n⚠️ IP CONFLICT DETECTED!" -ForegroundColor Red
    Write-Host "Your computer and ESP32 are using the same IP: $esp32IP" -ForegroundColor Red
    Write-Host "This is causing the MQTT connection to fail." -ForegroundColor Red
    Write-Host "`nSolutions:" -ForegroundColor Yellow
    Write-Host "1. Change your computer's IP address" -ForegroundColor White
    Write-Host "2. Or modify ESP32 code to use a different MQTT server IP" -ForegroundColor White
} else {
    Write-Host "`n✅ No IP conflict detected" -ForegroundColor Green
    Write-Host "Your computer is not using $esp32IP" -ForegroundColor Green
}

# Test MQTT connection to computer IPs
Write-Host "`nTesting MQTT connections:" -ForegroundColor Yellow
$computerIPs = $ipConfig.IPAddress | Where-Object {$_ -notlike "127.*" -and $_ -notlike "169.*"}
foreach ($ip in $computerIPs) {
    Write-Host "Testing $ip" -ForegroundColor Cyan
    try {
        $result = & ".\mosquitto_pub.exe" -h $ip -t test/quick -m "Quick test" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ MQTT successful on $ip" -ForegroundColor Green
        } else {
            Write-Host "  ✗ MQTT failed on $ip" -ForegroundColor Red
        }
    } catch {
        Write-Host "  ✗ Exception on $ip" -ForegroundColor Red
    }
}

Write-Host "`n=====================" -ForegroundColor Green
Read-Host "Press Enter to exit"