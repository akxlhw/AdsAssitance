@echo off
echo Killing all uvicorn processes...
taskkill /F /IM uvicorn.exe >nul 2>&1
timeout /t 2 /nobreak >nul
echo Done.
