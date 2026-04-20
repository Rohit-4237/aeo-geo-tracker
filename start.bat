@echo off
echo ========================================
echo   AEO/GEO Tracker - Starting Server
echo ========================================
echo.

cd /d "%~dp0backend"

if not exist ".env" (
    copy ".env.example" ".env" >nul
)

echo Installing / checking dependencies...
python -m pip install -r requirements.txt -q --prefer-binary --no-warn-script-location 2>nul

REM Kill any process already using port 3000
echo Clearing port 3000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000 "') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 /nobreak >nul

echo.
echo ----------------------------------------
echo  Server running at: http://localhost:3000
echo  Keep this window OPEN while using the tool.
echo  Press Ctrl+C to stop.
echo ----------------------------------------
echo.

start /b cmd /c "timeout /t 4 /nobreak >nul && start http://localhost:3000"

python -m uvicorn main:app --host 127.0.0.1 --port 3000

echo.
pause
