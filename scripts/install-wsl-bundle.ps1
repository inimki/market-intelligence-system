$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $PSScriptRoot
$Bundle = Join-Path $ProjectDir ".downloads\wsl\Microsoft.WSL_2.7.12.0_x64_ARM64.msixbundle"
$ExpectedHash = "deb1499e0fa081f7e7933e034195eb65b0302d84d8f2e9d5b3c5466bf6d952cc"

if (-not (Test-Path -LiteralPath $Bundle)) {
    throw "WSL bundle was not found at $Bundle"
}
$ActualHash = (Get-FileHash -LiteralPath $Bundle -Algorithm SHA256).Hash.ToLowerInvariant()
if ($ActualHash -ne $ExpectedHash) {
    throw "WSL bundle SHA256 mismatch."
}

Add-AppxPackage -Path $Bundle -ForceApplicationShutdown
Write-Host "Microsoft WSL package installation completed."
