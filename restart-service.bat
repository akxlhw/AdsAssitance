@echo off
setlocal

:: Switch to the directory where this script is located (worktree root)
cd /d "%~dp0"

echo ==========================================
echo  CoupangAds Web Service Restart Script
echo  Directory: %CD%
echo  URL:       http://127.0.0.1:8000
echo ==========================================
echo.

:: ===== Mock slowdown switches (only affect mock provider; real APIs ignore these) =====
:: Purpose: simulate real generation latency to test progress bar / SSE / timeout / retry UI.
:: Set to 0 (or comment out) to disable.

:: Seconds per mock image (real-world: 60-120s per image)
set COUPANGADS_MOCK_IMAGE_DELAY=60

:: Seconds per mock text step (report / title / keywords / selling_points / instagram)
set COUPANGADS_MOCK_TEXT_DELAY=3

:: Random failure rate for mock images (0~1), tests error-handling UI
set COUPANGADS_MOCK_IMAGE_FAIL_RATE=0.05

:: Random hang rate for mock images (0~1); hang triggers pipeline timeout skip
set COUPANGADS_MOCK_IMAGE_HANG_RATE=0.02

:: Per-image pipeline timeout in seconds (also applies to real API calls).
:: Hung or unresponsive images are skipped; pipeline continues.
set COUPANGADS_IMAGE_TIMEOUT_SEC=120

:: ===== End mock switches =====

:: Kill any running coupangads web processes (covers both python -m and uvicorn launches)
echo [1/3] Stopping existing service processes...
taskkill /F /IM uvicorn.exe >nul 2>&1
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*coupangads.web.app*' } | ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } catch {} }" >nul 2>&1
echo       Done.

:: Wait 2 seconds to ensure the port is released
ping -n 3 127.0.0.1 >nul

:: Activate the virtual environment
echo [2/3] Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment. Check venv\Scripts\activate.bat exists.
    pause
    exit /b 1
)

:: Start the service in a new window (--reload auto-reloads on source changes)
echo [3/3] Starting service...
echo   MOCK_IMAGE_DELAY     = %COUPANGADS_MOCK_IMAGE_DELAY%s / image
echo   MOCK_TEXT_DELAY      = %COUPANGADS_MOCK_TEXT_DELAY%s / step
echo   MOCK_IMAGE_FAIL_RATE = %COUPANGADS_MOCK_IMAGE_FAIL_RATE%
echo   MOCK_IMAGE_HANG_RATE = %COUPANGADS_MOCK_IMAGE_HANG_RATE%
echo   IMAGE_TIMEOUT_SEC    = %COUPANGADS_IMAGE_TIMEOUT_SEC%s
echo.
start "CoupangAds Service" cmd /k "python -m uvicorn coupangads.web.app:app --host 127.0.0.1 --port 8000 --reload"

echo.
echo Service started in a new window.
echo Open browser: http://127.0.0.1:8000
echo Close the "CoupangAds Service" window to stop the service.
echo.
echo Tip: change env values and rerun this script; no need to stop manually.
endlocal
