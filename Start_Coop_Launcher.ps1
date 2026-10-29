param(
    [switch]$CreateDesktopShortcut,
    [switch]$CheckOnly,
    [string]$DesktopDirectory = [Environment]::GetFolderPath('DesktopDirectory')
)

$ErrorActionPreference = 'Stop'
$launcherPath = Join-Path $PSScriptRoot 'CrysisCoopLauncher.py'
if (-not (Test-Path -LiteralPath $launcherPath)) {
    throw 'CrysisCoopLauncher.py is missing. Keep the launcher scripts inside the CrysisCoop mod folder.'
}

# Resolve the interpreter on this PC instead of sharing someone else's Python path.
$candidates = @()
$pyCommand = Get-Command py.exe -CommandType Application -ErrorAction SilentlyContinue
if ($pyCommand) {
    try {
        $pyPath = & $pyCommand.Source -3 -c 'import sys; print(sys.executable)' 2>$null
        if ($LASTEXITCODE -eq 0) { $candidates += $pyPath }
    } catch { }
}
foreach ($commandName in @('python.exe', 'python3.exe')) {
    $commands = Get-Command $commandName -CommandType Application -All -ErrorAction SilentlyContinue
    foreach ($command in $commands) {
        # Windows Store aliases can open the Store instead of running Python.
        if ($command.Source -notmatch '\\WindowsApps\\') { $candidates += $command.Source }
    }
}
foreach ($registryRoot in @('HKCU:\Software\Python\PythonCore', 'HKLM:\Software\Python\PythonCore', 'HKLM:\Software\WOW6432Node\Python\PythonCore')) {
    foreach ($versionKey in (Get-ChildItem -LiteralPath $registryRoot -ErrorAction SilentlyContinue)) {
        $installKey = Get-Item -LiteralPath ($versionKey.PSPath + '\InstallPath') -ErrorAction SilentlyContinue
        if ($installKey) {
            $registeredExe = $installKey.GetValue('ExecutablePath')
            if ($registeredExe) { $candidates += $registeredExe }
            elseif ($installKey.GetValue('')) { $candidates += Join-Path $installKey.GetValue('') 'python.exe' }
        }
    }
}

$pythonExe = $null
$pythonwExe = $null
foreach ($candidate in ($candidates | Select-Object -Unique)) {
    if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
    try {
        $probe = & $candidate -c 'import sys; sys.exit(1) if sys.version_info < (3, 10) else None; import tkinter; from PIL import Image, ImageTk; print(sys.executable)' 2>$null
        if ($LASTEXITCODE -ne 0 -or -not $probe) { continue }
        $windowedExe = Join-Path (Split-Path $probe -Parent) 'pythonw.exe'
        if (Test-Path -LiteralPath $windowedExe -PathType Leaf) {
            $pythonExe = $probe
            $pythonwExe = $windowedExe
            break
        }
    } catch { }
}
if (-not $pythonwExe) {
    throw 'Python 3.10+ with Tkinter and Pillow is required. Install Python from python.org with Tcl/Tk enabled, then run: python -m pip install Pillow. Run this launcher again afterward.'
}

if ($CheckOnly) {
    [pscustomobject]@{ Python = $pythonExe; PythonW = $pythonwExe; Launcher = $launcherPath }
    return
}

if ($CreateDesktopShortcut) {
    if (-not (Test-Path -LiteralPath $DesktopDirectory -PathType Container)) {
        throw 'The desktop directory could not be found. Supply -DesktopDirectory with an existing folder.'
    }
    $shortcutPath = Join-Path $DesktopDirectory 'Play Crysis Co-op.lnk'
    $shortcutShell = New-Object -ComObject WScript.Shell
    $shortcut = $shortcutShell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $pythonwExe
    $shortcut.Arguments = '"' + $launcherPath + '"'
    $shortcut.WorkingDirectory = $PSScriptRoot
    $shortcut.Description = 'Crysis Co-op launcher - Host, Join, and tactical loadouts'
    $iconPath = Join-Path $PSScriptRoot 'CrysisCoop.ico'
    if (Test-Path -LiteralPath $iconPath) { $shortcut.IconLocation = $iconPath + ',0' }
    $shortcut.Save()
    Write-Output ('Created desktop shortcut: ' + $shortcutPath)
    return
}

Start-Process -FilePath $pythonwExe -ArgumentList ('"' + $launcherPath + '"') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
