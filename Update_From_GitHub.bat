@echo off
title Update Crysis Co-op from GitHub
color 0a
echo ================================================================================
echo               CRYSIS CO-OP: FETCH LATEST UPDATES FROM GITHUB
echo ================================================================================
echo.

:: 1. Locate the CrysisCoop directory
set "MOD_DIR="

:: Check if running from inside Mods\CrysisCoop
if exist "%~dp0CrysisCoopLauncher.py" (
    set "MOD_DIR=%~dp0"
)

:: Check default Steam installation paths
if "%MOD_DIR%"=="" if exist "C:\Program Files (x86)\Steam\steamapps\common\Crysis\Mods\CrysisCoop\CrysisCoopLauncher.py" (
    set "MOD_DIR=C:\Program Files (x86)\Steam\steamapps\common\Crysis\Mods\CrysisCoop"
)
if "%MOD_DIR%"=="" if exist "C:\Program Files\Steam\steamapps\common\Crysis\Mods\CrysisCoop\CrysisCoopLauncher.py" (
    set "MOD_DIR=C:\Program Files\Steam\steamapps\common\Crysis\Mods\CrysisCoop"
)
if "%MOD_DIR%"=="" if exist "D:\Steam\steamapps\common\Crysis\Mods\CrysisCoop\CrysisCoopLauncher.py" (
    set "MOD_DIR=D:\Steam\steamapps\common\Crysis\Mods\CrysisCoop"
)
if "%MOD_DIR%"=="" if exist "D:\SteamLibrary\steamapps\common\Crysis\Mods\CrysisCoop\CrysisCoopLauncher.py" (
    set "MOD_DIR=D:\SteamLibrary\steamapps\common\Crysis\Mods\CrysisCoop"
)
if "%MOD_DIR%"=="" if exist "E:\SteamLibrary\steamapps\common\Crysis\Mods\CrysisCoop\CrysisCoopLauncher.py" (
    set "MOD_DIR=E:\SteamLibrary\steamapps\common\Crysis\Mods\CrysisCoop"
)

if "%MOD_DIR%"=="" (
    echo [ERROR] Could not automatically locate CrysisCoop mod folder!
    echo Please make sure Crysis is installed in Steam.
    pause
    exit /b 1
)

cd /d "%MOD_DIR%"
echo Found Crysis Co-op at: %MOD_DIR%
echo.

:: 2. Check if .git exists in the mod directory
if exist "%MOD_DIR%\.git" (
    echo [1/4] Git repository detected. Fetching latest commits from GitHub...
    git fetch origin main
    git reset --hard origin/main
    if %ERRORLEVEL% EQU 0 (
        echo [OK] Successfully updated via git!
    ) else (
        echo [!] Git pull had issues. Attempting direct GitHub ZIP update fallback...
        goto ZIP_UPDATE
    )
) else (
    goto ZIP_UPDATE
)
goto RUNTIME_CHECK

:ZIP_UPDATE
echo [1/4] Downloading latest update ZIP directly from GitHub...
powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object System.Net.WebClient).DownloadFile('https://github.com/MaxHavocc/Crysis-CO-OP/archive/refs/heads/main.zip', '$env:TEMP\CrysisCoop_main.zip')"
if exist "%TEMP%\CrysisCoop_main.zip" (
    echo [2/4] Extracting update files...
    powershell -Command "Expand-Archive -Path '$env:TEMP\CrysisCoop_main.zip' -DestinationPath '$env:TEMP\CrysisCoop_extract' -Force; Copy-Item -Path '$env:TEMP\CrysisCoop_extract\Crysis-CO-OP-main\*' -Destination '%MOD_DIR%' -Recurse -Force; Remove-Item -Path '$env:TEMP\CrysisCoop_main.zip', '$env:TEMP\CrysisCoop_extract' -Recurse -Force"
    echo [OK] ZIP update extracted successfully!
) else (
    echo [ERROR] Failed to download update from GitHub. Check your internet connection.
    pause
    exit /b 1
)

:RUNTIME_CHECK
echo [2/4] Checking co-op network runtime (CrysisCoop.exe)...
if not exist "%MOD_DIR%\..\..\Bin32\CrysisCoop.exe" (
    echo Installing co-op network runtime via Setup_Coop_Runtime.ps1...
    powershell -ExecutionPolicy Bypass -File "%MOD_DIR%\Setup_Coop_Runtime.ps1"
) else (
    echo [OK] Co-op network runtime is already installed!
)

:POST_UPDATE
echo [3/4] Skipping intro logo videos...
powershell -Command "$videoDir = Join-Path (Split-Path (Split-Path '%MOD_DIR%')) 'Game\Localized\Video'; if (Test-Path $videoDir) { Get-ChildItem -Path $videoDir -Recurse -Filter 'Trailer_*.sfd' | ForEach-Object { Move-Item -Path $_.FullName -Destination ($_.FullName + '.bak') -Force -ErrorAction SilentlyContinue } }"
echo [OK] Intro videos disabled.

echo [4/4] Setting up Desktop shortcuts...
powershell -ExecutionPolicy Bypass -File "%MOD_DIR%\Setup_Desktop_Shortcut.ps1" 2>nul

echo.
echo ================================================================================
echo [SUCCESS] Crysis Co-op has been updated to the latest version!
echo ================================================================================
echo.
pause
