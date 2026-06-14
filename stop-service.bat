@echo off
echo Stopping CoupangAds service processes...

:: Kill legacy uvicorn.exe launches
taskkill /F /IM uvicorn.exe >nul 2>&1

:: Kill any python process running coupangads web (covers `python -m coupangads.web.app`
:: and `python -m uvicorn coupangads.web.app:app`)
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*coupangads.web.app*' } | ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } catch {} }" >nul 2>&1

if %errorlevel% equ 0 (
    echo Service stopped.
) else (
    echo No matching process found.
)
pause
