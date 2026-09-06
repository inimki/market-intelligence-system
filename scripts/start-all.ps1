$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $PSScriptRoot
$LogDir = Join-Path $ProjectDir "data\logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$Services = @(
    @{
        Name = "主 API"
        Port = 8000
        Python = ".venv\Scripts\python.exe"
        App = "app.main:app"
        Log = "api"
    },
    @{
        Name = "网页采集器"
        Port = 8011
        Python = ".venv-collector\Scripts\python.exe"
        App = "app.collector_service:app"
        Log = "collector"
    },
    @{
        Name = "PandasAI 分析服务"
        Port = 8012
        Python = ".venv-ai\Scripts\python.exe"
        App = "app.ai_service:app"
        Log = "analysis"
    }
)

foreach ($Service in $Services) {
    $Existing = Get-NetTCPConnection -State Listen -LocalPort $Service.Port -ErrorAction SilentlyContinue
    if ($Existing) {
        Write-Host "[已运行] $($Service.Name)：http://127.0.0.1:$($Service.Port)"
        continue
    }

    $PythonPath = Join-Path $ProjectDir $Service.Python
    if (-not (Test-Path -LiteralPath $PythonPath)) {
        throw "缺少运行环境：$PythonPath"
    }

    Start-Process `
        -FilePath $PythonPath `
        -ArgumentList "-m", "uvicorn", $Service.App, "--host", "127.0.0.1", "--port", $Service.Port `
        -WorkingDirectory $ProjectDir `
        -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $LogDir "$($Service.Log).out.log") `
        -RedirectStandardError (Join-Path $LogDir "$($Service.Log).err.log")
}

$Deadline = (Get-Date).AddSeconds(30)
do {
    Start-Sleep -Milliseconds 500
    $ReadyPorts = @(
        Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
            Where-Object { $_.LocalPort -in 8000, 8011, 8012 } |
            Select-Object -ExpandProperty LocalPort -Unique
    )
} until ($ReadyPorts.Count -eq 3 -or (Get-Date) -gt $Deadline)

if ($ReadyPorts.Count -ne 3) {
    throw "服务未在 30 秒内全部启动，请查看 data\logs 下的错误日志。"
}

Write-Host ""
Write-Host "系统启动成功。"
Write-Host "API 文档：http://127.0.0.1:8000/docs"
Write-Host "最新报告：http://127.0.0.1:8000/reports/latest"
