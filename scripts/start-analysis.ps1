$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectDir
& ".\.venv-ai\Scripts\python.exe" -m uvicorn app.ai_service:app --host 127.0.0.1 --port 8012
