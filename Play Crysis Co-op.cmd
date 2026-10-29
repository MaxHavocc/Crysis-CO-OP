@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start_Coop_Launcher.ps1"
if errorlevel 1 (
    echo.
    echo The co-op launcher could not start. See the message above.
    pause
    exit /b 1
)
