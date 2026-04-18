@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0parse.ps1" %*
exit /b %errorlevel%
