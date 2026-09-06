@echo off
chcp 65001 >nul
cd /d "%~dp0.."
docker compose up -d
docker compose ps
echo.
echo 系统启动完成：
echo API:  http://127.0.0.1:8000/api/docs
echo n8n:  http://127.0.0.1:5678
echo 报告: http://127.0.0.1:8000/reports/latest
echo.
pause
