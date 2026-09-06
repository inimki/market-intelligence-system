$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $PSScriptRoot
$ExpectedApps = @{
    8000 = "app.main:app"
    8011 = "app.collector_service:app"
    8012 = "app.ai_service:app"
}

foreach ($Port in 8000, 8011, 8012) {
    $Connections = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
    if (-not $Connections) {
        Write-Host "[未运行] 端口 $Port"
        continue
    }

    foreach ($Connection in $Connections) {
        $ProcessInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$($Connection.OwningProcess)"
        $CommandLine = $ProcessInfo.CommandLine
        $ExpectedApp = $ExpectedApps[$Port]
        $ParentInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$($ProcessInfo.ParentProcessId)"
        $ParentCommandLine = $ParentInfo.CommandLine
        $IsExpectedChild = $CommandLine -like "*$ExpectedApp*" -and $CommandLine -like "*--port $Port*"
        $IsExpectedParent = $ParentCommandLine -like "*$ProjectDir*" -and $ParentCommandLine -like "*$ExpectedApp*"
        if (-not $IsExpectedChild -or -not $IsExpectedParent) {
            Write-Warning "端口 $Port 不是本项目进程，已跳过，未停止任何其他程序。"
            continue
        }
        Stop-Process -Id $Connection.OwningProcess
        Start-Sleep -Milliseconds 300
        if (Get-Process -Id $ParentInfo.ProcessId -ErrorAction SilentlyContinue) {
            Stop-Process -Id $ParentInfo.ProcessId
        }
        Write-Host "[已停止] $ExpectedApp（端口 $Port）"
    }
}
