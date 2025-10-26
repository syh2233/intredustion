# Simple Network Test for ESP32 MQTT
Write-Host "ESP32 MQTT Network Test" -ForegroundColor Green
Write-Host "=======================" -ForegroundColor Green

# Get computer IP
$ipConfig = Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias (Get-NetAdapter | Where-Object {$_.Status -eq "Up"}).Name
Write-Host "Computer IP Addresses:" -ForegroundColor Yellow
$ipConfig | Format-Table IPAddress, InterfaceAlias -AutoSize

# Test MQTT on each IP
$computerIPs = $ipConfig.IPAddress | Where-Object {$_ -notlike "127.*" -and $_ -notlike "169.*" -and $_ -notlike "172.*"}
Write-Host "`nTesting MQTT connections:" -ForegroundColor Yellow

foreach ($ip in $computerIPs) {
    Write-Host "Testing $ip`:1883..." -ForegroundColor Cyan
    try {
        $result = & ".\mosquitto_pub.exe" -h $ip -t test/network -m "Test message" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  SUCCESS: MQTT working on $ip" -ForegroundColor Green
            Write-Host "  Use this IP in ESP32 code: $ip" -ForegroundColor White
        } else {
            Write-Host "  FAILED: $result" -ForegroundColor Red
        }
    } catch {
        Write-Host "  ERROR: $_" -ForegroundColor Red
    }
}

Write-Host "`n=======================" -ForegroundColor Green
Read-Host "Press Enter to exit"