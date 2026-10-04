@echo off
title FinTrack - Server and Phone Tunnel
cd /d "%~dp0"
echo ===================================================
echo     FinTrack - Starting Server and Phone Link
echo ===================================================
echo.
echo Starting Flask Server in background...
start /b python app.py >nul 2>&1

echo Starting Cloudflare Tunnel...
echo (Your phone link will appear below in 2-3 seconds)
echo ---------------------------------------------------
cloudflared.exe tunnel --url http://127.0.0.1:5000
pause
