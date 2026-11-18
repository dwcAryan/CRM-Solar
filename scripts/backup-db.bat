@echo off
setlocal
cd /d "%~dp0"
python backup_db.py %*
if %ERRORLEVEL% neq 0 (
    pause
)
