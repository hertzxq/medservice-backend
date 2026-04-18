@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0parse-status.ps1" %*
exit /b %errorlevel%
