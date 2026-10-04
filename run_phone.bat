@echo off
title FinTrack Launcher
echo ========================================================
echo        FinTrack - Personal Finance Management
echo ========================================================
echo.
echo 1. Starting Flask Server on port 5000...
start "FinTrack Flask Server" cmd /k "cd /d %~dp0 && python app.py"

echo Waiting 3 seconds for server initialization...
timeout /t 3 /nobreak >nul

echo 2. Starting Cloudflare Tunnel for Phone Access...
start "FinTrack Cloudflare Tunnel" cmd /k "%LOCALAPPDATA%\Programs\Cloudflare\cloudflared.exe tunnel --url http://127.0.0.1:5000"

echo.
echo ========================================================
echo  Both services are now running!
echo  - Look at the "FinTrack Cloudflare Tunnel" window.
echo  - Copy the https://xxxx.trycloudflare.com link and open
echo    it in your phone browser!
echo  - To stop, close both command windows.
echo ========================================================
echo.
pause
