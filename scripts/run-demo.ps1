$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectDir
& ".\.venv\Scripts\python.exe" -m app demo --open
