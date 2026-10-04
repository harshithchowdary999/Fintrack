@echo off
title FinTrack Server & Phone Link
cd /d "%~dp0"
echo ======================================================
echo          FinTrack - Personal Finance System
echo ======================================================
echo.
echo Starting Flask Server in background...
start /b python app.py >nul 2>&1

echo.
echo Opening FinTrack in your browser...
start http://127.0.0.1:5000

echo.
echo ======================================================
echo   [1] Localhost URL : http://127.0.0.1:5000
echo   [2] Local Wi-Fi   : http://172.29.19.140:5000
echo   [3] Phone Link    : Generating secure tunnel...
echo ======================================================
echo.

python -u -c "import subprocess, re, sys, os; cf = subprocess.Popen(['cloudflared.exe', 'tunnel', '--url', 'http://127.0.0.1:5000'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True); [ (print('\n======================================================\n  YOUR PHONE LINK IS READY:\n\n     ' + re.search(r'https://[a-zA-Z0-9\-]+\.trycloudflare\.com', l).group(0) + '\n\n  Link automatically copied to clipboard!\n  Keep this window open while using FinTrack.\n======================================================\n', flush=True), os.system('powershell Set-Clipboard -Value ' + re.search(r'https://[a-zA-Z0-9\-]+\.trycloudflare\.com', l).group(0)), setattr(sys, 'found', True)) for l in iter(cf.stderr.readline, '') if re.search(r'https://[a-zA-Z0-9\-]+\.trycloudflare\.com', l) and not hasattr(sys, 'found') ]; cf.wait()"
pause
