param(
    [string]$DesktopDirectory = [Environment]::GetFolderPath('DesktopDirectory')
)

$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'Start_Coop_Launcher.ps1') -CreateDesktopShortcut -DesktopDirectory $DesktopDirectory
