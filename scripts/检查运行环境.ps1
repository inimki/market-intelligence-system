$ErrorActionPreference = "Continue"

$ProjectDir = Split-Path -Parent $PSScriptRoot
$EnvFile = Join-Path $ProjectDir ".env"
$script:HasFailure = $false

function Write-Pass([string]$Message) {
    Write-Host "[PASS] $Message" -ForegroundColor Green
}

function Write-Warn([string]$Message) {
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Fail([string]$Message) {
    Write-Host "[FAIL] $Message" -ForegroundColor Red
    $script:HasFailure = $true
}

function Get-EnvValue([string]$Name) {
    if (-not (Test-Path -LiteralPath $EnvFile)) {
        return $null
    }
    $Pattern = "^" + [regex]::Escape($Name) + "=(.*)$"
    $Line = Get-Content -LiteralPath $EnvFile -Encoding UTF8 |
        Where-Object { $_ -match $Pattern } |
        Select-Object -Last 1
    if ($null -eq $Line) {
        return $null
    }
    return ([regex]::Match($Line, $Pattern)).Groups[1].Value.Trim()
}

Write-Host "Market Intelligence System - Environment Check" -ForegroundColor Cyan
Write-Host "Project: $ProjectDir"
Write-Host "This script never prints or uploads API keys and passwords."
Write-Host ""

if ($env:OS -eq "Windows_NT") {
    Write-Pass "Windows detected"
}
else {
    Write-Fail "This checker is for Windows. Check Docker manually on Linux or macOS"
}

$Wsl = Get-Command wsl.exe -ErrorAction SilentlyContinue
if ($null -eq $Wsl) {
    Write-Fail "WSL was not found. Install WSL 2 and restart Windows"
}
else {
    & $Wsl.Source --status *> $null
    if ($LASTEXITCODE -eq 0) {
        Write-Pass "WSL is available"
    }
    else {
        Write-Fail "WSL is not ready. Run: wsl --status"
    }
}

$Docker = Get-Command docker.exe -ErrorAction SilentlyContinue
if ($null -eq $Docker) {
    Write-Fail "Docker CLI was not found. Install and start Docker Desktop"
}
else {
    Write-Pass "Docker CLI found"
    & $Docker.Source compose version *> $null
    if ($LASTEXITCODE -eq 0) {
        Write-Pass "Docker Compose V2 is available"
    }
    else {
        Write-Fail "Docker Compose V2 is unavailable"
    }

    & $Docker.Source info *> $null
    if ($LASTEXITCODE -eq 0) {
        Write-Pass "Docker Engine is running"
    }
    else {
        Write-Fail "Docker Engine is not running. Open Docker Desktop and wait for Engine running"
    }
}

$Git = Get-Command git.exe -ErrorAction SilentlyContinue
if ($null -eq $Git) {
    Write-Warn "Git was not found. ZIP download works, but git clone requires Git"
}
else {
    Write-Pass "Git is available"
}

try {
    $Computer = Get-CimInstance Win32_ComputerSystem -ErrorAction Stop
    $MemoryGb = [math]::Round($Computer.TotalPhysicalMemory / 1GB, 1)
    if ($MemoryGb -ge 8) {
        Write-Pass "Physical memory: ${MemoryGb} GB"
    }
    else {
        Write-Warn "Physical memory is ${MemoryGb} GB; at least 8 GB is recommended"
    }
}
catch {
    Write-Warn "Unable to read physical memory information"
}

try {
    $Drive = Get-Item -LiteralPath $ProjectDir | Select-Object -ExpandProperty PSDrive
    $FreeGb = [math]::Round($Drive.Free / 1GB, 1)
    if ($FreeGb -ge 15) {
        Write-Pass "Free disk space: ${FreeGb} GB"
    }
    else {
        Write-Warn "Only ${FreeGb} GB is free; at least 15 GB is recommended for the first build"
    }
}
catch {
    Write-Warn "Unable to read free disk space"
}

if (-not (Test-Path -LiteralPath $EnvFile)) {
    Write-Fail "Missing .env. Run: Copy-Item .env.example .env"
}
else {
    Write-Pass ".env exists"

    $EncryptionKey = Get-EnvValue "N8N_ENCRYPTION_KEY"
    if ([string]::IsNullOrWhiteSpace($EncryptionKey) -or
        $EncryptionKey -eq "change-this-to-a-long-random-string" -or
        $EncryptionKey.Length -lt 32) {
        Write-Fail "N8N_ENCRYPTION_KEY is unchanged or shorter than 32 characters"
    }
    else {
        Write-Pass "N8N_ENCRYPTION_KEY is configured (value hidden)"
    }

    $DatabasePassword = Get-EnvValue "POSTGRES_PASSWORD"
    if ([string]::IsNullOrWhiteSpace($DatabasePassword) -or
        $DatabasePassword -eq "change-this-password" -or
        $DatabasePassword.Length -lt 12) {
        Write-Fail "POSTGRES_PASSWORD is unchanged or shorter than 12 characters"
    }
    else {
        Write-Pass "POSTGRES_PASSWORD is configured (value hidden)"
    }

    $AiKey = Get-EnvValue "AI_API_KEY"
    if ([string]::IsNullOrWhiteSpace($AiKey)) {
        Write-Warn "AI_API_KEY is empty. Basic collection/reporting works; Browser Use and PandasAI do not"
    }
    else {
        $Provider = Get-EnvValue "AI_PROVIDER"
        $Model = Get-EnvValue "AI_MODEL"
        Write-Pass "AI key is configured (value hidden); provider=$Provider, model=$Model"
    }
}

foreach ($Port in @(8000, 5678)) {
    try {
        $Listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
        if ($null -ne $Listener) {
            Write-Warn "Port $Port is in use. Ignore this only when this project is already running"
        }
        else {
            Write-Pass "Port $Port is available"
        }
    }
    catch {
        Write-Warn "Unable to inspect port $Port"
    }
}

Write-Host ""
if ($script:HasFailure) {
    Write-Host "Environment check failed. Fix each [FAIL] item and run this script again." -ForegroundColor Red
    exit 1
}

Write-Host "Required checks passed. You can run scripts\finish-docker-n8n.ps1." -ForegroundColor Green
exit 0
