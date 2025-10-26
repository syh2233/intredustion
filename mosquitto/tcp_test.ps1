# TCP连接测试工具
Write-Host "TCP连接测试工具" -ForegroundColor Green
Write-Host "==============" -ForegroundColor Green

$testIPs = @(
    "127.0.0.1",
    "192.168.24.1",
    "192.168.24.2",
    "192.168.24.23",
    "192.168.24.100"
)

$port = 1883

Write-Host "测试端口 $port 的TCP连接..." -ForegroundColor Yellow
Write-Host ""

foreach ($ip in $testIPs) {
    Write-Host "测试 $ip:$port..." -ForegroundColor Cyan

    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $connectResult = $tcpClient.BeginConnect($ip, $port, $null, $null)
        $waitResult = $connectResult.AsyncWaitHandle.WaitOne(3000) # 3秒超时

        if ($waitResult) {
            try {
                $tcpClient.EndConnect($connectResult)
                Write-Host "  ✅ TCP连接成功" -ForegroundColor Green
                $tcpClient.Close()

                # 测试MQTT连接
                $result = & ".\mosquitto_pub.exe" -h $ip -p $port -t test/tcp -m "TCP test" 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "  ✅ MQTT连接成功" -ForegroundColor Green
                } else {
                    Write-Host "  ❌ MQTT连接失败: $result" -ForegroundColor Red
                }
            } catch {
                Write-Host "  ❌ 连接后异常: $_" -ForegroundColor Red
                $tcpClient.Close()
            }
        } else {
            Write-Host "  ❌ TCP连接超时" -ForegroundColor Red
            $tcpClient.Close()
        }
    } catch {
        Write-Host "  ❌ TCP连接异常: $_" -ForegroundColor Red
    }

    Write-Host ""
}

Write-Host "如果192.168.24.23显示连接成功，说明有IP地址冲突" -ForegroundColor Yellow
Write-Host "ESP32和电脑不能使用相同的IP地址" -ForegroundColor Yellow

Write-Host "==============" -ForegroundColor Green
Read-Host "按 Enter 键退出"