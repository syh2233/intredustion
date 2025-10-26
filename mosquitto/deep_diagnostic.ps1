# Deep diagnostic for Mosquitto connection issues
Write-Host "Deep Diagnostic for Mosquitto Connection Issues" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green

Set-Location $PSScriptRoot

# 1. Check Mosquitto process details
Write-Host "1. Mosquitto Process Details:" -ForegroundColor Yellow
$mosquittoProcesses = Get-Process | Where-Object {$_.Name -like "*mosquitto*"}
if ($mosquittoProcesses) {
    foreach ($process in $mosquittoProcesses) {
        Write-Host "Process: $($process.Name) (PID: $($process.Id))" -ForegroundColor Green
        Write-Host "  Start Time: $($process.StartTime)"
        Write-Host "  Path: $($process.Path)"
        Write-Host "  Command Line: $(Get-WmiObject Win32_Process -Filter "ProcessId=$($process.Id)" | Select-Object -ExpandProperty CommandLine)"
        Write-Host ""
    }
} else {
    Write-Host "No Mosquitto processes found" -ForegroundColor Red
}

# 2. Check port listeners in detail
Write-Host "2. Detailed Port Listening Status:" -ForegroundColor Yellow
$netstatResult = netstat -an | findstr ":1883"
if ($netstatResult) {
    Write-Host "Port 1883 listening status:" -ForegroundColor Green
    $netstatResult | ForEach-Object {
        Write-Host "  $_"
    }
} else {
    Write-Host "Port 1883 not found in netstat" -ForegroundColor Red
}

# 3. Test with different connection parameters
Write-Host "3. Testing with different connection parameters:" -ForegroundColor Yellow

$testConfigs = @(
    @{Host = "127.0.0.1"; Port = 1883; Name = "Localhost"},
    @{Host = "localhost"; Port = 1883; Name = "Localhost DNS"},
    @{Host = "192.168.24.23"; Port = 1883; Name = "Network IP"},
    @{Host = "0.0.0.0"; Port = 1883; Name = "All Interfaces"}
)

foreach ($config in $testConfigs) {
    Write-Host "Testing $($config.Name) ($($config.Host):$($config.Port))..." -ForegroundColor Cyan

    # Test with telnet-like approach using TCP
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $connectResult = $tcpClient.BeginConnect($config.Host, $config.Port, $null, $null)
        $waitResult = $connectResult.AsyncWaitHandle.WaitOne(3000) # 3 second timeout

        if ($waitResult) {
            try {
                $tcpClient.EndConnect($connectResult)
                Write-Host "  ✓ TCP Connection successful" -ForegroundColor Green
                $tcpClient.Close()
            } catch {
                Write-Host "  ✗ TCP Connection failed after connect: $_" -ForegroundColor Red
            }
        } else {
            Write-Host "  ✗ TCP Connection timeout" -ForegroundColor Red
            $tcpClient.Close()
        }
    } catch {
        Write-Host "  ✗ TCP Connection exception: $_" -ForegroundColor Red
    }

    # Test with mosquitto_pub
    try {
        $result = & ".\mosquitto_pub.exe" -h $config.Host -p $config.Port -t test/deep -m "Deep test" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ MQTT Publish successful" -ForegroundColor Green
        } else {
            Write-Host "  ✗ MQTT Publish failed" -ForegroundColor Red
            Write-Host "    Error: $result" -ForegroundColor Red
        }
    } catch {
        Write-Host "  ✗ MQTT Publish exception: $_" -ForegroundColor Red
    }

    Write-Host ""
}

# 4. Check Windows Firewall
Write-Host "4. Windows Firewall Status:" -ForegroundColor Yellow
try {
    $firewallStatus = netsh advfirewall show allprofiles state
    Write-Host "Firewall profiles:" -ForegroundColor Cyan
    $firewallStatus | ForEach-Object {
        if ($_ -match "State") {
            Write-Host "  $_"
        }
    }

    # Check for specific Mosquitto rules
    Write-Host "`nChecking for Mosquitto firewall rules:" -ForegroundColor Cyan
    $firewallRules = netsh advfirewall firewall show rule name=all | findstr -i mosquitto
    if ($firewallRules) {
        Write-Host "Found Mosquitto firewall rules:" -ForegroundColor Green
        $firewallRules | ForEach-Object {
            Write-Host "  $_"
        }
    } else {
        Write-Host "No Mosquitto firewall rules found" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Error checking firewall: $_" -ForegroundColor Red
}

# 5. Check network interfaces
Write-Host "`n5. Network Interfaces:" -ForegroundColor Yellow
$adapters = Get-NetAdapter | Where-Object {$_.Status -eq "Up"}
foreach ($adapter in $adapters) {
    Write-Host "Adapter: $($adapter.Name)" -ForegroundColor Cyan
    Write-Host "  Status: $($adapter.Status)"
    Write-Host "  LinkSpeed: $($adapter.LinkSpeed)"

    $ipAddresses = Get-NetIPAddress -InterfaceAlias $adapter.Name -AddressFamily IPv4 -ErrorAction SilentlyContinue
    if ($ipAddresses) {
        Write-Host "  IP Addresses:"
        foreach ($ip in $ipAddresses) {
            Write-Host "    $($ip.IPAddress)/$($ip.PrefixLength)"
        }
    }
    Write-Host ""
}

# 6. Try to restart Mosquitto with minimal config
Write-Host "6. Recommendation: Restart Mosquitto with minimal config" -ForegroundColor Yellow
Write-Host "Consider stopping current Mosquitto and restarting with:" -ForegroundColor Cyan
Write-Host "mosquitto.exe -c mosquitto_simple.conf -v" -ForegroundColor White
Write-Host ""
Write-Host "Or create a minimal config with only:" -ForegroundColor Cyan
Write-Host "listener 1883" -ForegroundColor White
Write-Host "allow_anonymous true" -ForegroundColor White

Write-Host "================================================" -ForegroundColor Green
Write-Host "Diagnostic completed!" -ForegroundColor Green
Write-Host ""
Read-Host "Press Enter to exit"