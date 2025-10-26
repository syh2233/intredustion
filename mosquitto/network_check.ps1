# 网络配置检查脚本
Write-Host "网络配置检查" -ForegroundColor Green
Write-Host "==============" -ForegroundColor Green

# 1. 检查电脑的IP配置
Write-Host "1. 电脑IP配置:" -ForegroundColor Yellow
$ipConfig = Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias (Get-NetAdapter | Where-Object {$_.Status -eq "Up"}).Name
$ipConfig | Format-Table IPAddress, InterfaceAlias, PrefixLength -AutoSize

# 2. 检查当前WiFi连接
Write-Host "`n2. WiFi连接状态:" -ForegroundColor Yellow
$wifiProfile = netsh wlan show interfaces | findstr "SSID"
Write-Host $wifiProfile

# 3. 检查路由表
Write-Host "`n3. 路由表信息:" -ForegroundColor Yellow
$routeInfo = route print | findstr "192.168.24"
Write-Host $routeInfo

# 4. 检查端口监听
Write-Host "`n4. 端口监听状态:" -ForegroundColor Yellow
$portInfo = netstat -an | findstr ":1883"
Write-Host $portInfo

# 5. 检查ESP32可能使用的IP范围
Write-Host "`n5. ESP32 IP地址分析:" -ForegroundColor Yellow
Write-Host "ESP32获得的IP: 192.168.24.23" -ForegroundColor Red
Write-Host "如果这个地址与电脑冲突，需要修改DHCP范围" -ForegroundColor Yellow

# 6. 建议的解决方案
Write-Host "`n6. 建议的解决方案:" -ForegroundColor Cyan
Write-Host "方案1: 修改ESP32代码中的MQTT服务器地址为电脑的IP" -ForegroundColor White
Write-Host "方案2: 修改路由器DHCP设置，避免IP冲突" -ForegroundColor White
Write-Host "方案3: 使用不同的MQTT端口" -ForegroundColor White

# 7. 测试电脑的MQTT服务器
Write-Host "`n7. 测试电脑MQTT服务器:" -ForegroundColor Yellow
$computerIPs = $ipConfig.IPAddress | Where-Object {$_ -notlike "127.*" -and $_ -notlike "169.*"}
foreach ($ip in $computerIPs) {
    Write-Host "测试连接到: $ip" -ForegroundColor Cyan
    try {
        $result = & ".\mosquitto_pub.exe" -h $ip -t test/local -m "Test message" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✅ 成功连接到 $ip" -ForegroundColor Green
        } else {
            Write-Host "  ❌ 连接 $ip 失败: $result" -ForegroundColor Red
        }
    } catch {
        Write-Host "  ❌ 连接 $ip 异常: $_" -ForegroundColor Red
    }
}

Write-Host "`n==============" -ForegroundColor Green
Read-Host "按 Enter 键退出"