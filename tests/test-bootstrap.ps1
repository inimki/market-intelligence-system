$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot
$TempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
$TestDir = Join-Path $TempRoot ("market-intel-bootstrap-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $TestDir | Out-Null
try {
    Copy-Item -LiteralPath (Join-Path $ProjectDir ".env.example") -Destination $TestDir
    $InitScript = Join-Path $ProjectDir "scripts\init-env.ps1"
    & $InitScript -ProjectDir $TestDir
    $EnvPath = Join-Path $TestDir ".env"
    $Content = [IO.File]::ReadAllText($EnvPath)
    $Password = [regex]::Match($Content, '(?m)^POSTGRES_PASSWORD=([0-9a-f]{64})\r?$')
    $Key = [regex]::Match($Content, '(?m)^N8N_ENCRYPTION_KEY=([0-9a-f]{64})\r?$')
    if (-not $Password.Success -or -not $Key.Success) { throw "Random hex credentials missing" }
    if ($Password.Groups[1].Value -eq $Key.Groups[1].Value) { throw "Credentials are not independent" }
    if ($Content -notmatch '(?m)^AI_API_KEY=\r?$') { throw "Fresh installation should have no AI key" }
    $Before = (Get-FileHash -LiteralPath $EnvPath).Hash
    & $InitScript -ProjectDir $TestDir
    if ((Get-FileHash -LiteralPath $EnvPath).Hash -ne $Before) { throw "Existing .env was modified" }
    foreach ($Name in @("deploy.ps1", "init-env.ps1", "finish-docker-n8n.ps1", "verify-learn.ps1")) {
        $ParseErrors = $null
        [Management.Automation.Language.Parser]::ParseFile((Join-Path $ProjectDir "scripts\$Name"), [ref]$null, [ref]$ParseErrors) | Out-Null
        if ($ParseErrors.Count) { throw "PowerShell parse failed: $Name" }
    }
    Write-Host "PASS: fresh environment, independent random credentials, no key, idempotency, script parsing."
} finally {
    $Resolved = [IO.Path]::GetFullPath($TestDir)
    if (-not $Resolved.StartsWith($TempRoot, [StringComparison]::OrdinalIgnoreCase) -or
        (Split-Path -Leaf $Resolved) -notlike "market-intel-bootstrap-*") {
        throw "Unexpected test cleanup target"
    }
    Remove-Item -LiteralPath $Resolved -Recurse -Force
}
