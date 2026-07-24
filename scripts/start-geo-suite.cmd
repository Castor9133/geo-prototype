@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-geo-suite.ps1" %*
exit /b %ERRORLEVEL%
