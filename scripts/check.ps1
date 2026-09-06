$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectDir
& ".\.venv\Scripts\python.exe" -m ruff check app tests
& ".\.venv\Scripts\python.exe" -m pytest -q
