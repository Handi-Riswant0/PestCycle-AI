@echo off
cd /d "%~dp0"
echo ==========================================
echo        PESTCYCLE AI - START ALL
echo ==========================================
start "PestCycle AI Backend" cmd /k "cd /d ""%~dp0backend"" && run_api.bat"
timeout /t 3 /nobreak >nul
start "PestCycle AI Frontend" cmd /k "cd /d ""%~dp0"" && npm.cmd install && npm.cmd run dev"
echo.
echo Backend : http://127.0.0.1:8000
echo API Docs: http://127.0.0.1:8000/docs
echo Dashboard: http://localhost:5173
echo.
pause
