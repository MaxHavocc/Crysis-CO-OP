@echo off
title Update Crysis Co-op from GitHub
color 0a
echo ================================================================================
echo               CRYSIS CO-OP: FETCH LATEST UPDATES FROM GITHUB
echo ================================================================================
echo.

cd /d "%~dp0"

echo Pulling latest code, scripts, launcher, and engine DLL...
git pull origin main

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ================================================================================
    echo [SUCCESS] Mod is up to date with the latest GitHub version!
    echo ================================================================================
) else (
    echo.
    echo ================================================================================
    echo [WARNING] Git pull encountered an error. Check your network or git status.
    echo ================================================================================
)

echo.
pause
