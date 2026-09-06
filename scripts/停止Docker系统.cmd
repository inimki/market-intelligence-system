@echo off
chcp 65001 >nul
cd /d "%~dp0.."
docker compose stop
echo.
echo 五个容器已经停止，数据库和报告仍然保留。
echo.
pause
