$ErrorActionPreference = "Stop"

$TaskName = "MarketIntel-Finish-N8n-Once"
$ProjectDir = Split-Path -Parent $PSScriptRoot
$LogDir = Join-Path $ProjectDir "data\logs"
$LogFile = Join-Path $LogDir "post-reboot-docker-n8n.log"
$FinishScript = Join-Path $PSScriptRoot "finish-docker-n8n.ps1"
$InstallWslScript = Join-Path $PSScriptRoot "install-wsl-bundle.ps1"

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
Start-Transcript -Path $LogFile -Append
try {
    Write-Host "Starting one-time post-reboot Docker and n8n setup."
    $WslCheck = Start-Process `
        -FilePath "$env:SystemRoot\System32\wsl.exe" `
        -ArgumentList "--version" `
        -WindowStyle Hidden `
        -Wait `
        -PassThru
    if ($WslCheck.ExitCode -ne 0) {
        Write-Host "Installing the verified local WSL package after restart..."
        & $InstallWslScript
        $WslCheck = Start-Process `
            -FilePath "$env:SystemRoot\System32\wsl.exe" `
            -ArgumentList "--version" `
            -WindowStyle Hidden `
            -Wait `
            -PassThru
        if ($WslCheck.ExitCode -ne 0) {
            throw "WSL did not become available after local package installation."
        }
    }
    & $FinishScript
    if ($LASTEXITCODE -ne 0) {
        throw "The Docker/n8n finish script returned exit code $LASTEXITCODE."
    }
    Write-Host "One-time post-reboot setup completed successfully."
}
catch {
    Write-Error $_
}
finally {
    try {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    }
    finally {
        Stop-Transcript
    }
}
