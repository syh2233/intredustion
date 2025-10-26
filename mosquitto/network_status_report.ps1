# ESP32 MQTT网络状态报告
Write-Host "ESP32 MQTT网络状态报告" -ForegroundColor Green
Write-Host "======================" -ForegroundColor Green

# 1. 检查计算机IP配置
Write-Host "`n1. 计算机IP配置:" -ForegroundColor Yellow
$ipConfig = Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias (Get-NetAdapter | Where-Object {$_.Status -eq "Up"}).Name
$ipConfig | Format-Table IPAddress, InterfaceAlias, PrefixLength -AutoSize

# 2. 检查Mosquitto服务状态
Write-Host "`n2. Mosquitto服务状态:" -ForegroundColor Yellow
$mosquittoProcess = Get-Process -Name "mosquitto" -ErrorAction SilentlyContinue
if ($mosquittoProcess) {
    Write-Host "✅ Mosquitto进程正在运行 (PID: $($mosquittoProcess.Id))" -ForegroundColor Green
} else {
    Write-Host "❌ Mosquitto进程未运行" -ForegroundColor Red
}

# 3. 检查端口监听状态
Write-Host "`n3. 端口1883监听状态:" -ForegroundColor Yellow
$portListeners = Get-NetTCPConnection -LocalPort 1883 -ErrorAction SilentlyContinue
if ($portListeners) {
    $portListeners | Format-Table LocalAddress, LocalPort, State, OwningProcess -AutoSize
} else {
    Write-Host "❌ 端口1883未在监听" -ForegroundColor Red
}

# 4. 测试MQTT连接
Write-Host "`n4. MQTT连接测试:" -ForegroundColor Yellow
$computerIPs = $ipConfig.IPAddress | Where-Object {$_ -notlike "127.*" -and $_ -notlike "169.*" -and $_ -notlike "172.*"}
foreach ($ip in $computerIPs) {
    Write-Host "测试 $ip`:1883..." -ForegroundColor Cyan
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $connectResult = $tcpClient.BeginConnect($ip, 1883, $null, $null)
        $waitResult = $connectResult.AsyncWaitHandle.WaitOne(3000)

        if ($waitResult) {
            try {
                $tcpClient.EndConnect($connectResult)
                Write-Host "  ✅ TCP连接成功" -ForegroundColor Green
                $tcpClient.Close()

                # 测试MQTT协议
                $result = & ".\mosquitto_pub.exe" -h $ip -t test/report -m "Network status test" 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "  ✅ MQTT协议正常" -ForegroundColor Green
                } else {
                    Write-Host "  ❌ MQTT协议失败: $result" -ForegroundColor Red
                }
            } catch {
                Write-Host "  ❌ 连接异常: $_" -ForegroundColor Red
            }
        } else {
            Write-Host "  ❌ TCP连接超时" -ForegroundColor Red
            $tcpClient.Close()
        }
    } catch {
        Write-Host "  ❌ TCP连接异常: $_" -ForegroundColor Red
    }
}

# 5. 生成ESP32配置建议
Write-Host "`n5. ESP32配置建议:" -ForegroundColor Cyan
$workingIP = $computerIPs | Where-Object {
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $connectResult = $tcpClient.BeginConnect($_, 1883, $null, $null)
        $waitResult = $connectResult.AsyncWaitHandle.WaitOne(2000)
        if ($waitResult) {
            $tcpClient.EndConnect($connectResult)
            $tcpClient.Close()
            $true
        } else {
            $tcpClient.Close()
            $false
        }
    } catch {
        $false
    }
}

if ($workingIP) {
    Write-Host "建议ESP32使用以下MQTT服务器配置:" -ForegroundColor White
    Write-Host "  MQTT_SERVER = `"$workingIP`"" -ForegroundColor Yellow
    Write-Host "  MQTT_PORT = 1883" -ForegroundColor Yellow
    Write-Host "  WIFI_SSID = `"syh2031`"" -ForegroundColor Yellow
    Write-Host "  WIFI_PASSWORD = `"12345678`"" -ForegroundColor Yellow
} else {
    Write-Host "❌ 没有找到可用的MQTT服务器地址" -ForegroundColor Red
}

Write-Host "`n======================" -ForegroundColor Green
Read-Host "按 Enter 键退出"