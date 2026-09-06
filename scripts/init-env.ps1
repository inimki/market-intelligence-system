param(
    [string]$ProjectDir = (Split-Path -Parent $PSScriptRoot)
)
$ErrorActionPreference = "Stop"
$EnvFile = Join-Path $ProjectDir ".env"

function New-RandomHex {
    $Bytes = New-Object byte[] 32
    $Generator = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $Generator.GetBytes($Bytes) } finally { $Generator.Dispose() }
    return [BitConverter]::ToString($Bytes).Replace("-", "").ToLowerInvariant()
}

if (Test-Path -LiteralPath $EnvFile) {
    Write-Host "Existing .env preserved. Keys and database passwords are unchanged."
    return
}

$Content = [IO.File]::ReadAllText((Join-Path $ProjectDir ".env.example"))
$Content = $Content.Replace("change-this-password", (New-RandomHex))
$Content = $Content.Replace("change-this-to-a-long-random-string", (New-RandomHex))
# CreateNew prevents accidentally overwriting configuration created concurrently.
$Stream = [IO.File]::Open($EnvFile, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write)
try {
    $Bytes = (New-Object Text.UTF8Encoding($false)).GetBytes($Content)
    $Stream.Write($Bytes, 0, $Bytes.Length)
} finally { $Stream.Dispose() }
Write-Host "Created local .env with random credentials. AI is optional and initially disabled."
