@echo off
echo Stopping CoupangAds background service...
taskkill /F /IM uvicorn.exe >nul 2>&1
if %errorlevel% equ 0 (
    echo Service stopped.
) else (
    echo No running uvicorn process found.
)
pause
