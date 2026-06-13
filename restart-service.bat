@echo off
setlocal

:: Switch to the directory where this script is located (worktree root)
cd /d "%~dp0"

echo ==========================================
echo  CoupangAds Web Service Restart Script
echo  Directory: %CD%
echo  URL:       http://127.0.0.1:8080
echo ==========================================
echo.

:: Kill any running uvicorn processes
echo [1/3] Stopping existing uvicorn processes...
taskkill /F /IM uvicorn.exe >nul 2>&1
if %errorlevel% equ 0 (
    echo       Old process stopped.
) else (
    echo       No running uvicorn process found.
)

:: Wait 1 second to ensure the port is released
ping -n 2 127.0.0.1 >nul

:: Activate the virtual environment
echo [2/3] Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment. Check venv\Scripts\activate.bat exists.
    pause
    exit /b 1
)

:: Start the Uvicorn service in a minimized window
echo [3/3] Starting Uvicorn background service...
start /min "CoupangAds Service" cmd /k "uvicorn coupangads.web.app:app --host 127.0.0.1 --port 8080 --reload"

echo.
echo Service started in a minimized window.
echo Open browser: http://127.0.0.1:8080
echo Close the "CoupangAds Service" window to stop the service.
endlocal
