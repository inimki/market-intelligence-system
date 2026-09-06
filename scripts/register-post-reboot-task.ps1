$ErrorActionPreference = "Stop"

$TaskName = "MarketIntel-Finish-N8n-Once"
$PostRebootScript = Join-Path $PSScriptRoot "post-reboot-setup.ps1"
$PowerShellExe = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$UserId = "$env:USERDOMAIN\$env:USERNAME"

if (-not (Test-Path -LiteralPath $PostRebootScript)) {
    throw "Post-reboot script was not found at $PostRebootScript"
}

$Action = New-ScheduledTaskAction `
    -Execute $PowerShellExe `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$PostRebootScript`""
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $UserId
$Principal = New-ScheduledTaskPrincipal `
    -UserId $UserId `
    -LogonType Interactive `
    -RunLevel Highest

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Principal $Principal `
    -Description "One-time Docker Desktop startup, Compose deployment, and n8n workflow import." `
    -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName"
