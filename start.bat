@echo off
title FinTrack Phone Link
cd /d "%~dp0"
echo ===================================================
echo     FinTrack - Starting Server and Phone Link
echo ===================================================
echo.
echo Starting Flask Server in background...
start /b python app.py >nul 2>&1

echo Generating secure phone link (2-3 seconds)...
python -u -c "import subprocess, re, sys, os; cf = subprocess.Popen(['cloudflared.exe', 'tunnel', '--url', 'http://127.0.0.1:5000'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True); [ (print('\n======================================================\n  YOUR PHONE LINK IS READY:\n\n     ' + re.search(r'https://[a-zA-Z0-9\-]+\.trycloudflare\.com', l).group(0) + '\n\n  Link copied to clipboard!\n  Keep this window open while using the app.\n======================================================\n', flush=True), os.system('powershell Set-Clipboard -Value ' + re.search(r'https://[a-zA-Z0-9\-]+\.trycloudflare\.com', l).group(0)), setattr(sys, 'found', True)) for l in iter(cf.stderr.readline, '') if re.search(r'https://[a-zA-Z0-9\-]+\.trycloudflare\.com', l) and not hasattr(sys, 'found') ]; cf.wait()"
pause
