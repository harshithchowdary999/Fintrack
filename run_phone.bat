@echo off
title FinTrack Launcher
cd /d "%~dp0"

echo ========================================================
echo        FinTrack - Personal Finance Management
echo ========================================================
echo.
echo [1/2] Starting Flask Server...
start "FinTrack Flask Server" cmd /k "cd /d "%~dp0" && python app.py"

echo Waiting for Flask to initialize...
ping 127.0.0.1 -n 3 >nul

echo [2/2] Starting Cloudflare Tunnel...
start "FinTrack Cloudflare Tunnel" cmd /k "cd /d "%~dp0" && cloudflared.exe tunnel --url http://127.0.0.1:5000"

echo.
echo ========================================================
echo  SUCCESS: Both services are running!
echo.
echo  Option A (Any Network / 4G / 5G):
echo  - Look at the "FinTrack Cloudflare Tunnel" window.
echo  - Copy the https://xxxx.trycloudflare.com link.
echo.
echo  Option B (Same Wi-Fi / Hotspot - Never Changes):
echo  - Open on phone: http://172.29.19.140:5000
echo.
echo  (Leave both windows open while using the app.)
echo  (To stop everything, simply close the windows.)
echo ========================================================
echo.
pause
