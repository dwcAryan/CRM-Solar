@echo off
setlocal
cd /d "%~dp0"
python restore_db.py %*
if %ERRORLEVEL% neq 0 (
    pause
)
