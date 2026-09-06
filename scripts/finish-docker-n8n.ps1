$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $PSScriptRoot
$ComposeFile = Join-Path $ProjectDir "docker-compose.yml"
$DockerCommand = Get-Command docker.exe -ErrorAction SilentlyContinue
$DockerExe = if ($null -ne $DockerCommand) {
    $DockerCommand.Source
}
else {
    "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
}
$DockerDesktop = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
$WorkflowName = "市场情报自动收集与报告"
$WorkflowId = "marketIntelDaily01"

if (-not (Test-Path -LiteralPath $DockerExe)) {
    throw "Docker CLI was not found at $DockerExe"
}
if (-not (Test-Path -LiteralPath $ComposeFile)) {
    throw "Compose file was not found at $ComposeFile"
}
if (-not (Test-Path -LiteralPath (Join-Path $ProjectDir ".env"))) {
    throw "Missing .env. Copy .env.example to .env and configure it before installation."
}

Write-Host "[1/6] Checking WSL and Docker Desktop..."
$WslCheck = Start-Process `
    -FilePath "$env:SystemRoot\System32\wsl.exe" `
    -ArgumentList "--version" `
    -WindowStyle Hidden `
    -Wait `
    -PassThru
if ($WslCheck.ExitCode -ne 0) {
    throw "WSL is not ready. Restart Windows once, then run this script again."
}

function Test-DockerReady {
    $DockerCheck = Start-Process `
        -FilePath $DockerExe `
        -ArgumentList "info" `
        -WindowStyle Hidden `
        -Wait `
        -PassThru
    return $DockerCheck.ExitCode -eq 0
}

if (-not (Test-DockerReady)) {
    if (-not (Test-Path -LiteralPath $DockerDesktop)) {
        throw "Docker Desktop was not found at $DockerDesktop"
    }
    Start-Process -FilePath $DockerDesktop -WindowStyle Hidden
}

$DockerReady = $false
for ($Attempt = 1; $Attempt -le 60; $Attempt++) {
    if (Test-DockerReady) {
        $DockerReady = $true
        break
    }
    Start-Sleep -Seconds 5
}
if (-not $DockerReady) {
    throw "Docker Desktop did not become ready within five minutes. Open Docker Desktop and check its message."
}

Write-Host "[2/6] Stopping the local Python services that would occupy port 8000..."
$StopScript = Join-Path $PSScriptRoot "stop-all.ps1"
if (Test-Path -LiteralPath $StopScript) {
    & $StopScript
}

Write-Host "[3/6] Starting PostgreSQL, API services, and n8n (missing images are built automatically)..."
& $DockerExe compose --project-directory $ProjectDir -f $ComposeFile up -d
if ($LASTEXITCODE -ne 0) {
    throw "docker compose up failed."
}

Write-Host "[4/6] Waiting for n8n health check..."
$N8nReady = $false
for ($Attempt = 1; $Attempt -le 60; $Attempt++) {
    try {
        $Response = Invoke-WebRequest -Uri "http://127.0.0.1:5678/healthz" -UseBasicParsing -TimeoutSec 5
        if ($Response.StatusCode -eq 200) {
            $N8nReady = $true
            break
        }
    }
    catch {
        Start-Sleep -Seconds 5
    }
}
if (-not $N8nReady) {
    & $DockerExe compose --project-directory $ProjectDir -f $ComposeFile logs --tail 120 n8n
    throw "n8n did not become healthy within five minutes."
}

$ApiReady = $false
for ($Attempt = 1; $Attempt -le 60; $Attempt++) {
    try {
        $ApiHealth = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 5
        if ($ApiHealth.status -eq "ok") {
            $ApiReady = $true
            break
        }
    }
    catch {
        Start-Sleep -Seconds 5
    }
}
if (-not $ApiReady) {
    throw "The market-intelligence API did not become healthy within five minutes."
}

$Sources = @(Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/sources" -TimeoutSec 15)
if ($Sources.Count -eq 0) {
    Write-Host "Seeding three official public news sources..."
    $DefaultSources = @(
        @{name = "施耐德电气中国新闻中心"; url = "https://www.se.com/cn/zh/about-us/newsroom/news/"; kind = "static"; enabled = $true; tags = @("中国官网", "目标公司", "能源管理", "工业自动化")},
        @{name = "西门子中文新闻中心"; url = "https://news.siemens.com/zh-cn/"; kind = "static"; enabled = $true; tags = @("中文新闻", "竞争对手", "工业自动化", "数字化")},
        @{name = "ABB 中国新闻中心"; url = "https://new.abb.com/cn/news-center"; kind = "static"; enabled = $true; tags = @("中国官网", "竞争对手", "电气化", "自动化")}
    )
    foreach ($Source in $DefaultSources) {
        $Body = $Source | ConvertTo-Json -Depth 4 -Compress
        Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/sources" -ContentType "application/json" -Body $Body -TimeoutSec 30 | Out-Null
    }
}

Write-Host "[5/6] Importing the workflow if it is not already present..."
$ExistingWorkflows = (& $DockerExe compose --project-directory $ProjectDir -f $ComposeFile exec -T n8n n8n export:workflow --all 2>&1 | Out-String)
$WorkflowExportExitCode = $LASTEXITCODE
if ($WorkflowExportExitCode -ne 0 -and $ExistingWorkflows -notmatch "No workflows found") {
    throw "Unable to inspect existing n8n workflows."
}
if ($ExistingWorkflows -notmatch [regex]::Escape($WorkflowName)) {
    & $DockerExe compose --project-directory $ProjectDir -f $ComposeFile exec -T n8n n8n import:workflow --input=/files/workflows/market-intelligence.json
    if ($LASTEXITCODE -ne 0) {
        throw "n8n workflow import failed."
    }
    # n8n 2.x separates importing a draft from publishing its schedule. The
    # one-off CLI process needs port 5679, so stop the main process briefly,
    # publish, and then bring the editor back up.
    & $DockerExe compose --project-directory $ProjectDir -f $ComposeFile stop n8n
    & $DockerExe compose --project-directory $ProjectDir -f $ComposeFile run --rm --no-deps n8n publish:workflow "--id=$WorkflowId"
    $PublishExitCode = $LASTEXITCODE
    & $DockerExe compose --project-directory $ProjectDir -f $ComposeFile up -d n8n
    if ($PublishExitCode -ne 0 -or $LASTEXITCODE -ne 0) {
        throw "n8n workflow publish or restart failed."
    }
}
else {
    Write-Host "Workflow already exists; import skipped."
}

Write-Host "[6/6] Final container status..."
& $DockerExe compose --project-directory $ProjectDir -f $ComposeFile ps
if ($LASTEXITCODE -ne 0) {
    throw "Unable to read the final Compose status."
}

Write-Host "Done. Open n8n at http://127.0.0.1:5678"
Write-Host "Latest market-intelligence report: http://127.0.0.1:8000/reports/latest"
