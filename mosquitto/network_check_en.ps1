# Network Configuration Check Script
Write-Host "Network Configuration Check" -ForegroundColor Green
Write-Host "=========================" -ForegroundColor Green

# 1. Check computer IP configuration
Write-Host "1. Computer IP Configuration:" -ForegroundColor Yellow
$ipConfig = Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias (Get-NetAdapter | Where-Object {$_.Status -eq "Up"}).Name
$ipConfig | Format-Table IPAddress, InterfaceAlias, PrefixLength -AutoSize

# 2. Check current WiFi connection
Write-Host "`n2. WiFi Connection Status:" -ForegroundColor Yellow
$wifiProfile = netsh wlan show interfaces | findstr "SSID"
Write-Host $wifiProfile

# 3. Check routing table
Write-Host "`n3. Routing Table Information:" -ForegroundColor Yellow
$routeInfo = route print | findstr "192.168.24"
Write-Host $routeInfo

# 4. Check port listening
Write-Host "`n4. Port Listening Status:" -ForegroundColor Yellow
$portInfo = netstat -an | findstr ":1883"
Write-Host $portInfo

# 5. Analyze ESP32 IP address
Write-Host "`n5. ESP32 IP Address Analysis:" -ForegroundColor Yellow
Write-Host "ESP32 got IP: 192.168.24.23" -ForegroundColor Red
Write-Host "If this conflicts with computer, need to modify DHCP range" -ForegroundColor Yellow

# 6. Recommended solutions
Write-Host "`n6. Recommended Solutions:" -ForegroundColor Cyan
Write-Host "Option 1: Modify ESP32 code to use computer's actual IP" -ForegroundColor White
Write-Host "Option 2: Modify router DHCP settings to avoid IP conflict" -ForegroundColor White
Write-Host "Option 3: Use different MQTT port" -ForegroundColor White

# 7. Test computer's MQTT server
Write-Host "`n7. Test Computer MQTT Server:" -ForegroundColor Yellow
$computerIPs = $ipConfig.IPAddress | Where-Object {$_ -notlike "127.*" -and $_ -notlike "169.*"}
foreach ($ip in $computerIPs) {
    Write-Host "Testing connection to: $ip" -ForegroundColor Cyan
    try {
        $result = & ".\mosquitto_pub.exe" -h $ip -t test/local -m "Test message" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ Successfully connected to $ip" -ForegroundColor Green
        } else {
            Write-Host "  ✗ Failed to connect to $ip: $result" -ForegroundColor Red
        }
    } catch {
        Write-Host "  ✗ Exception connecting to $ip: $_" -ForegroundColor Red
    }
}

Write-Host "`n=========================" -ForegroundColor Green
Read-Host "Press Enter to exit"