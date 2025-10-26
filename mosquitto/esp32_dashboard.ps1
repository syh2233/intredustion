# ESP32 实时监控仪表板
Write-Host "ESP32 实时监控仪表板" -ForegroundColor Green
Write-Host "=========================" -ForegroundColor Green

Set-Location $PSScriptRoot

# 创建数据显示对象
$data = @{
    lastMessage = $null
    messageCount = 0
    lastAlert = $null
    alertCount = 0
    startTime = Get-Date
}

Write-Host "开始监控 ESP32 数据..." -ForegroundColor Yellow
Write-Host "按 Ctrl+C 停止监控" -ForegroundColor Cyan
Write-Host ""

# 创建后台作业来监控MQTT消息
$monitorJob = Start-Job -ScriptBlock {
    param($mosquittoPath)
    cd $mosquittoPath
    & ".\mosquitto_sub.exe" -h 127.0.0.1 -t "esp32/#" -v
} -ArgumentList $PSScriptRoot

# 显示实时数据
try {
    while ($true) {
        # 检查作业状态
        if ($monitorJob.State -ne "Running") {
            Write-Host "监控作业已停止" -ForegroundColor Red
            break
        }

        # 获取作业输出
        $output = Receive-Job $monitorJob -ErrorAction SilentlyContinue

        # 处理输出
        foreach ($line in $output) {
            if ($line -match "esp32/fire_alarm/data") {
                try {
                    $jsonData = $line.Substring($line.IndexOf("{"))
                    $message = $jsonData | ConvertFrom-Json

                    $data.lastMessage = $message
                    $data.messageCount++

                    # 显示数据
                    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] 📊 传感器数据" -ForegroundColor Cyan
                    Write-Host "  设备: $($message.device_id)" -ForegroundColor White
                    Write-Host "  温度: $($message.data.temperature)°C" -ForegroundColor White
                    Write-Host "  湿度: $($message.data.humidity)%" -ForegroundColor White
                    Write-Host "  火焰: $($message.data.flame)" -ForegroundColor White
                    Write-Host "  烟雾: $($message.data.smoke)" -ForegroundColor White
                    Write-Host "  状态: $($message.status.system_status)" -ForegroundColor White
                    Write-Host "  原因: $($message.status.status_reason)" -ForegroundColor White
                    Write-Host ""

                } catch {
                    # 忽略JSON解析错误
                }
            }
            elseif ($line -match "esp32/fire_alarm/alert") {
                try {
                    $jsonData = $line.Substring($line.IndexOf("{"))
                    $message = $jsonData | ConvertFrom-Json

                    $data.lastAlert = $message
                    $data.alertCount++

                    # 显示警报
                    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] 🚨 火灾警报!" -ForegroundColor Red
                    Write-Host "  设备: $($message.device_id)" -ForegroundColor White
                    Write-Host "  温度: $($message.data.temperature)°C" -ForegroundColor White
                    Write-Host "  湿度: $($message.data.humidity)%" -ForegroundColor White
                    Write-Host "  状态: $($message.status.system_status)" -ForegroundColor White
                    Write-Host "  原因: $($message.status.status_reason)" -ForegroundColor White
                    Write-Host ""

                    # 发出提示音（如果支持）
                    [console]::beep(1000, 200)

                } catch {
                    # 忽略JSON解析错误
                }
            }
        }

        # 显示统计信息
        $uptime = (Get-Date) - $data.startTime
        Write-Host -NoNewline "监控时间: $($uptime.ToString('hh\:mm\:ss')) | "
        Write-Host -NoNewline "消息数: $($data.messageCount) | "
        Write-Host -NoNewline "警报数: $($data.alertCount) | "
        Write-Host "状态: 运行中" -ForegroundColor Green

        # 等待1秒
        Start-Sleep -Seconds 1

        # 清除当前行以便更新统计信息
        $currentLine = $Host.UI.RawUI.CursorPosition.Y
        $Host.UI.RawUI.CursorPosition = New-Object System.Management.Automation.Host.Coordinates 0, ($currentLine - 1)
    }
} catch {
    Write-Host "监控异常: $_" -ForegroundColor Red
} finally {
    # 清理作业
    if ($monitorJob) {
        Stop-Job $monitorJob
        Remove-Job $monitorJob
    }
}

Write-Host ""
Write-Host "监控已停止" -ForegroundColor Red
Read-Host "按 Enter 键退出"