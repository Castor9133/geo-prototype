@echo off
echo === GEORank: enable WSL2 + start Docker ===
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
wsl --install --no-distribution
echo.
echo If this is the first WSL install, REBOOT Windows, then start Docker Desktop,
echo then run: cd /d "C:\Cursor local\GEORank" ^& docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
pause
