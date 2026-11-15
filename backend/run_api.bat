@echo off
cd /d "%~dp0"
if not exist venv\Scripts\python.exe (
  py -3 -m venv venv
)
venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
  echo Gagal memasang dependensi backend. Periksa koneksi internet dan requirements.txt.
  pause
  exit /b 1
)
venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
pause
