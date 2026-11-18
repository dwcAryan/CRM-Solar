@echo off
setlocal
cd /d "%~dp0"
title Solar CRM Runner

python run.py %*
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Solar CRM exited with error code %ERRORLEVEL%.
    pause
)
