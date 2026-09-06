param([switch]$NoBrowser)
$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $ProjectDir

try {
    Write-Host "Market Intelligence - one-click Docker deployment" -ForegroundColor Cyan
    $DockerCommand = Get-Command docker.exe -ErrorAction SilentlyContinue
    if (-not $DockerCommand) {
        $DockerBin = "C:\Program Files\Docker\Docker\resources\bin"
        if (Test-Path -LiteralPath (Join-Path $DockerBin "docker.exe")) {
            $env:PATH = $DockerBin + ";" + $env:PATH
        } else {
            throw "Install Docker Desktop first: https://docs.docker.com/desktop/setup/install/windows-install/ . Enable WSL 2, restart Windows if requested, then double-click the launcher again."
        }
    }
    & docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        $Desktop = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
        if (Test-Path -LiteralPath $Desktop) {
            Start-Process -FilePath $Desktop -WindowStyle Hidden
        }
        Write-Host "Waiting for Docker Desktop (up to 3 minutes)..."
        $Ready = $false
        for ($Attempt = 0; $Attempt -lt 36; $Attempt++) {
            & docker info *> $null
            if ($LASTEXITCODE -eq 0) { $Ready = $true; break }
            Start-Sleep -Seconds 5
        }
        if (-not $Ready) { throw "Docker Engine is unavailable. Check Docker Desktop, WSL 2 and CPU virtualization." }
    }
    & docker compose version *> $null
    if ($LASTEXITCODE -ne 0) { throw "Docker Compose V2 is required. Update Docker Desktop." }

    & (Join-Path $PSScriptRoot "init-env.ps1")
    $LocalConfig = [IO.File]::ReadAllText((Join-Path $ProjectDir ".env"))
    foreach ($Name in @("POSTGRES_PASSWORD", "N8N_ENCRYPTION_KEY")) {
        $Match = [regex]::Match($LocalConfig, "(?m)^" + $Name + "=([^\r\n]+)")
        if (-not $Match.Success -or $Match.Groups[1].Value -match "^change-this") {
            throw "Set $Name in the existing .env. Existing database credentials will not be rotated automatically."
        }
    }
    $WebPort = 8080
    $PortMatch = [regex]::Match($LocalConfig, "(?m)^WEB_PORT=(\d+)\s*$")
    if ($PortMatch.Success) { $WebPort = [int]$PortMatch.Groups[1].Value }
    if ($WebPort -lt 1 -or $WebPort -gt 65535) { throw "WEB_PORT must be between 1 and 65535." }
    & docker compose config --quiet
    if ($LASTEXITCODE -ne 0) { throw "Invalid Compose configuration. Review .env without sharing its secrets." }

    # The existing installer also seeds sources and imports/publishes the schedule.
    & (Join-Path $PSScriptRoot "finish-docker-n8n.ps1")
    $Url = "http://127.0.0.1:$WebPort"
    $Healthy = $false
    for ($Attempt = 0; $Attempt -lt 30; $Attempt++) {
        try {
            $Health = Invoke-RestMethod -Uri "$Url/health" -TimeoutSec 5
            if ($Health.status -eq "ok") { $Healthy = $true; break }
        } catch { Start-Sleep -Seconds 2 }
    }
    if (-not $Healthy) { throw "Nginx is not ready. Run: docker compose logs --tail 80 nginx api" }
    & docker compose exec -T nginx nginx -t
    if ($LASTEXITCODE -ne 0) { throw "Nginx configuration validation failed." }
    Write-Host "Ready: $Url" -ForegroundColor Green
    Write-Host "Help: $Url/help | n8n: http://127.0.0.1:5678"
    Write-Host "Optional: configure AI_* in .env, then run this launcher again."
    if (-not $NoBrowser) { Start-Process $Url }
} catch {
    Write-Host ("Deployment failed: " + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
