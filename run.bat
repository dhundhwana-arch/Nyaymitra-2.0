@echo off
REM NYAYMITRA 2.0 - local launcher (Windows)
setlocal
set PORT=%1
if "%PORT%"=="" set PORT=8000
cd /d "%~dp0"

if not exist .venv (
  echo ==^> creating virtual environment
  python -m venv .venv
)
call .venv\Scripts\activate.bat
echo ==^> installing dependencies
pip install --quiet -r backend\requirements.txt
echo ==^> migrating database
python scripts\init_db.py --json >NUL
echo ==^> NYAYMITRA listening on http://127.0.0.1:%PORT%
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port %PORT%
endlocal
