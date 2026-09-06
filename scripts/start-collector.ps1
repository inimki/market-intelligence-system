$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectDir
& ".\.venv-collector\Scripts\python.exe" -m uvicorn app.collector_service:app --host 127.0.0.1 --port 8011
