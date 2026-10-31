[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ClientPublicKey,
    [Parameter(Mandatory = $true)][string]$ClientVpnAddress,
    [string]$CrysisRoot,
    [string]$HostVpnAddress,
    [switch]$ValidateOnly
)

$ErrorActionPreference = 'Stop'
$keyMarker = 'crysis-coop-bridge-v1'
$bridgeDirectory = Join-Path $env:ProgramData 'CrysisCoopBridge'
$utf8 = New-Object Text.UTF8Encoding($false)

function Assert-VpnAddress([string]$Address) {
    $parsed = $null
    if (-not [Net.IPAddress]::TryParse($Address, [ref]$parsed) -or
        $parsed.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork -or
        -not $Address.StartsWith('26.')) {
        throw 'Use an IPv4 address assigned by Radmin VPN (26.x.x.x).'
    }
}

function Find-CrysisRoot {
    $candidates = @()
    $scriptFolder = $PSScriptRoot
    for ($depth = 0; $depth -lt 5 -and $scriptFolder; $depth++) {
        $candidates += $scriptFolder
        $scriptFolder = Split-Path $scriptFolder -Parent
    }
    $steamFolders = @((Join-Path ${env:ProgramFiles(x86)} 'Steam'))
    foreach ($registryPath in @('HKCU:\Software\Valve\Steam', 'HKLM:\SOFTWARE\WOW6432Node\Valve\Steam')) {
        $steamRegistry = Get-ItemProperty -LiteralPath $registryPath -ErrorAction SilentlyContinue
        if ($steamRegistry.SteamPath) { $steamFolders += $steamRegistry.SteamPath }
        if ($steamRegistry.InstallPath) { $steamFolders += $steamRegistry.InstallPath }
    }
    foreach ($steamFolder in ($steamFolders | Select-Object -Unique)) {
        $candidates += Join-Path $steamFolder 'steamapps\common\Crysis'
        $librariesFile = Join-Path $steamFolder 'steamapps\libraryfolders.vdf'
        if (Test-Path -LiteralPath $librariesFile) {
            foreach ($match in [regex]::Matches([IO.File]::ReadAllText($librariesFile), '"path"\s+"([^"]+)"')) {
                $libraryPath = $match.Groups[1].Value.Replace('\\', '\')
                $candidates += Join-Path $libraryPath 'steamapps\common\Crysis'
            }
        }
    }
    $found = @($candidates | Select-Object -Unique | Where-Object {
        (Test-Path -LiteralPath (Join-Path $_ 'Bin32\CrySystem.dll')) -and
        (Test-Path -LiteralPath (Join-Path $_ 'Mods\CrysisCoop\CrysisCoopLauncher.py'))
    } | ForEach-Object { (Resolve-Path -LiteralPath $_).Path } | Select-Object -Unique)
    if ($found.Count -ne 1) { throw 'Could not select one Crysis installation. Supply -CrysisRoot with the game folder.' }
    return $found[0]
}

function Find-BridgePython {
    $candidates = @()
    $py = Get-Command py.exe -CommandType Application -ErrorAction SilentlyContinue
    if ($py) {
        try {
            $detected = & $py.Source -3 -c 'import sys; print(sys.executable)' 2>$null
            if ($LASTEXITCODE -eq 0) { $candidates += $detected }
        } catch { }
    }
    foreach ($commandName in @('python.exe', 'python3.exe')) {
        foreach ($command in (Get-Command $commandName -CommandType Application -All -ErrorAction SilentlyContinue)) {
            if ($command.Source -notmatch '\\WindowsApps\\') { $candidates += $command.Source }
        }
    }
    foreach ($registryRoot in @('HKCU:\Software\Python\PythonCore', 'HKLM:\Software\Python\PythonCore', 'HKLM:\Software\WOW6432Node\Python\PythonCore')) {
        foreach ($versionKey in (Get-ChildItem -LiteralPath $registryRoot -ErrorAction SilentlyContinue)) {
            $installKey = Get-Item -LiteralPath ($versionKey.PSPath + '\InstallPath') -ErrorAction SilentlyContinue
            if ($installKey) {
                if ($installKey.GetValue('ExecutablePath')) { $candidates += $installKey.GetValue('ExecutablePath') }
                elseif ($installKey.GetValue('')) { $candidates += Join-Path $installKey.GetValue('') 'python.exe' }
            }
        }
    }
    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
        try {
            $result = & $candidate -c 'import sys; sys.exit(1) if sys.version_info < (3, 10) else None; print(sys.executable)' 2>$null
            if ($LASTEXITCODE -eq 0 -and $result) { return [string]$result }
        } catch { }
    }
    throw 'Python 3.10+ was not found. Install Python for this Windows account, then run setup again.'
}

function Set-AdminOnlyAcl([string]$Path, [bool]$Directory = $false) {
    if ($Directory) { $acl = New-Object Security.AccessControl.DirectorySecurity }
    else { $acl = New-Object Security.AccessControl.FileSecurity }
    $acl.SetAccessRuleProtection($true, $false)
    $adminSid = New-Object Security.Principal.SecurityIdentifier('S-1-5-32-544')
    $systemSid = New-Object Security.Principal.SecurityIdentifier('S-1-5-18')
    $acl.SetOwner($adminSid)
    foreach ($sid in @($adminSid, $systemSid)) {
        if ($Directory) {
            $rule = New-Object Security.AccessControl.FileSystemAccessRule($sid, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow')
        } else {
            $rule = New-Object Security.AccessControl.FileSystemAccessRule($sid, 'FullControl', 'Allow')
        }
        $acl.AddAccessRule($rule)
    }
    Set-Acl -LiteralPath $Path -AclObject $acl
}

Assert-VpnAddress $ClientVpnAddress
if ($ClientPublicKey.Trim() -notmatch '^ssh-ed25519 ([A-Za-z0-9+/]+={0,2})(?: [^\r\n]*)?$') {
    throw 'Supply one ssh-ed25519 public key, without authorized_keys options or newlines.'
}
$keyBody = $Matches[1]
$keyBytes = [Convert]::FromBase64String($keyBody)
if ($keyBytes.Length -ne 51 -or [Text.Encoding]::ASCII.GetString($keyBytes, 4, 11) -ne 'ssh-ed25519' -or
    $keyBytes[0] -ne 0 -or $keyBytes[1] -ne 0 -or $keyBytes[2] -ne 0 -or $keyBytes[3] -ne 11 -or
    $keyBytes[15] -ne 0 -or $keyBytes[16] -ne 0 -or $keyBytes[17] -ne 0 -or $keyBytes[18] -ne 32) {
    throw 'The supplied Ed25519 public-key encoding is invalid.'
}

if (-not $CrysisRoot) { $CrysisRoot = Find-CrysisRoot }
$CrysisRoot = (Resolve-Path -LiteralPath $CrysisRoot).Path
$modRoot = Join-Path $CrysisRoot 'Mods\CrysisCoop'
if (-not (Test-Path -LiteralPath (Join-Path $CrysisRoot 'Bin32\CrySystem.dll')) -or
    -not (Test-Path -LiteralPath (Join-Path $modRoot 'CrysisCoopLauncher.py'))) {
    throw 'The selected folder must contain Crysis Bin32 and Mods\CrysisCoop.'
}
$agentSource = Join-Path $PSScriptRoot 'bridge_agent.py'
if (-not (Test-Path -LiteralPath $agentSource -PathType Leaf)) { throw 'Keep bridge_agent.py beside this setup script.' }
$pythonExe = Find-BridgePython
$vpnAddresses = @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -like '26.*' } | Select-Object -ExpandProperty IPAddress -Unique)
if (-not $vpnAddresses) {
    $ipconfigText = (& ipconfig.exe) -join "`n"
    $vpnAddresses = @([regex]::Matches($ipconfigText, '(?m)^.*IPv4[^:]*:\s*(26\.\d{1,3}\.\d{1,3}\.\d{1,3})\s*$') |
        ForEach-Object { $_.Groups[1].Value } | Select-Object -Unique)
}
if (-not $HostVpnAddress) {
    if ($vpnAddresses.Count -ne 1) { throw 'Connect Radmin VPN or supply -HostVpnAddress when multiple VPN addresses exist.' }
    $HostVpnAddress = $vpnAddresses[0]
}
Assert-VpnAddress $HostVpnAddress
if ($vpnAddresses -notcontains $HostVpnAddress) { throw 'HostVpnAddress is not assigned to this PC. Connect Radmin VPN first.' }
if ($HostVpnAddress -eq $ClientVpnAddress) { throw 'Host and client VPN addresses must be different.' }
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$sshUser = $identity.Name.ToLowerInvariant()
if ($sshUser -match '[\r\n,]') { throw 'This Windows username cannot be represented by the setup connection check.' }

if ($ValidateOnly) {
    [pscustomobject]@{ crysis_root = $CrysisRoot; mod_root = $modRoot; python_exe = $pythonExe;
        host_user = $sshUser; host = $HostVpnAddress; client_vpn_address = $ClientVpnAddress;
        agent_source = $agentSource; bridge_directory = $bridgeDirectory } | ConvertTo-Json
    return
}
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this setup in PowerShell as Administrator using the Windows account Caden normally uses.'
}

$sshDirectory = Join-Path $env:ProgramData 'ssh'
$sshdConfig = Join-Path $sshDirectory 'sshd_config'
$hadConfig = Test-Path -LiteralPath $sshdConfig
$hadDefaultRule = $null -ne (Get-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -ErrorAction SilentlyContinue)
$sshdExe = Join-Path $env:WINDIR 'System32\OpenSSH\sshd.exe'
$installedServer = $false
if (-not (Test-Path -LiteralPath $sshdExe)) {
    Write-Host 'Installing the Windows OpenSSH Server optional feature...'
    $installation = Add-WindowsCapability -Online -Name 'OpenSSH.Server~~~~0.0.1.0'
    $installedServer = $true
    if ($installation.RestartNeeded) { throw 'Windows requires a restart to finish OpenSSH installation. Restart, then rerun this same setup.' }
}
if (-not (Test-Path -LiteralPath $sshdExe)) { throw 'OpenSSH Server installation did not provide sshd.exe.' }
$sshKeygen = Join-Path (Split-Path $sshdExe -Parent) 'ssh-keygen.exe'
New-Item -ItemType Directory -Path $sshDirectory -Force | Out-Null
if (-not $hadConfig) {
    $initialConfig = @"
Port 22
ListenAddress $HostVpnAddress
PubkeyAuthentication yes
PasswordAuthentication no
PermitEmptyPasswords no
AuthorizedKeysFile __PROGRAMDATA__/ssh/administrators_authorized_keys
LogLevel VERBOSE
Subsystem sftp sftp-server.exe
"@
    [IO.File]::WriteAllText($sshdConfig, $initialConfig + "`r`n", $utf8)
    Set-AdminOnlyAcl $sshdConfig
}
# Do not preserve the broad firewall opening created by a fresh optional-feature install.
if ($installedServer -and -not $hadDefaultRule) {
    Get-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -ErrorAction SilentlyContinue | Disable-NetFirewallRule | Out-Null
}
& $sshKeygen -A
if ($LASTEXITCODE -ne 0) { throw 'Could not create the OpenSSH host keys.' }
& $sshdExe -t -f $sshdConfig
if ($LASTEXITCODE -ne 0) { throw 'OpenSSH configuration validation failed. Existing configuration was not replaced.' }
$effectiveConfig = @(& $sshdExe -T -f $sshdConfig -C "user=$sshUser,host=$env:COMPUTERNAME,addr=$ClientVpnAddress")
if ($LASTEXITCODE -ne 0) { throw 'Could not inspect effective OpenSSH settings for this Windows account.' }
$portLines = @($effectiveConfig | Where-Object { $_ -match '^port \d+$' })
if (-not $portLines) { throw 'Could not determine the OpenSSH listening port.' }
$sshPort = [int]($portLines[0] -split ' ')[1]
if ($effectiveConfig -contains 'pubkeyauthentication no') { throw 'Existing SSH configuration disables public-key authentication. No existing setting was changed.' }
if (@($effectiveConfig | Where-Object { $_ -match '^forcecommand ' -and $_ -ne 'forcecommand none' }).Count -gt 0) {
    throw 'Existing SSH has a ForceCommand that would override the bridge. No existing setting was changed.'
}
$hostKeyCandidates = @($effectiveConfig | Where-Object { $_ -match '^hostkey ' } | ForEach-Object {
    ($_ -replace '^hostkey ', '').Replace('__PROGRAMDATA__', $env:ProgramData).Replace('/', '\') + '.pub'
} | Where-Object { Test-Path -LiteralPath $_ })
$hostPublicKeyPath = $hostKeyCandidates | Where-Object { [IO.File]::ReadAllText($_).StartsWith('ssh-ed25519 ') } | Select-Object -First 1
if (-not $hostPublicKeyPath) { $hostPublicKeyPath = $hostKeyCandidates | Select-Object -First 1 }
if (-not $hostPublicKeyPath) { throw 'Could not read a host public key from the effective OpenSSH configuration.' }
$hostKeyFields = ([IO.File]::ReadAllText($hostPublicKeyPath).Trim() -split '\s+')
$hostPublicKey = $hostKeyFields[0] + ' ' + $hostKeyFields[1]
$fingerprintOutput = (& $sshKeygen -lf $hostPublicKeyPath -E sha256) -join ' '
if ($LASTEXITCODE -ne 0 -or $fingerprintOutput -notmatch '(SHA256:[A-Za-z0-9+/]+)') { throw 'Could not verify the SSH host-key fingerprint.' }
$fingerprint = $Matches[1]
$authorizedSetting = ($effectiveConfig | Where-Object { $_ -match '^authorizedkeysfile ' } | Select-Object -First 1) -replace '^authorizedkeysfile ', ''
$authorizedPaths = @([regex]::Matches($authorizedSetting, '"[^"]+"|\S+') | ForEach-Object { $_.Value.Trim('"') })
$keysFile = $null
foreach ($authorizedPath in $authorizedPaths) {
    $expanded = $authorizedPath.Replace('__PROGRAMDATA__', $env:ProgramData).Replace('%h', $env:USERPROFILE).Replace('%u', $env:USERNAME).Replace('/', '\')
    if (-not [IO.Path]::IsPathRooted($expanded)) { $expanded = Join-Path $env:USERPROFILE $expanded }
    $expanded = [IO.Path]::GetFullPath($expanded)
    if ($expanded -eq (Join-Path $sshDirectory 'administrators_authorized_keys') -or
        $expanded -eq (Join-Path $env:USERPROFILE '.ssh\authorized_keys')) { $keysFile = $expanded; break }
}
if (-not $keysFile) { throw 'Existing SSH uses a custom authorized-key location. Setup stopped without changing those keys.' }

New-Item -ItemType Directory -Path $bridgeDirectory -Force | Out-Null
Set-AdminOnlyAcl $bridgeDirectory $true
$agentTarget = Join-Path $bridgeDirectory 'bridge_agent.py'
$dispatcherPath = Join-Path $bridgeDirectory 'Dispatch.ps1'
$bridgeConfig = Join-Path $bridgeDirectory 'config.json'
Copy-Item -LiteralPath $agentSource -Destination $agentTarget -Force
$dispatcher = @'
$ErrorActionPreference = 'Stop'
$configPath = Join-Path $PSScriptRoot 'config.json'
$config = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ([Security.Principal.WindowsIdentity]::GetCurrent().Name.ToLowerInvariant() -ne $config.host_user) {
    Write-Output '{"ok":false,"error":"This bridge key is not authorized for this Windows account."}'
    exit 1
}
$env:PYTHONUTF8 = '1'
& $config.python_exe -I -B (Join-Path $PSScriptRoot 'bridge_agent.py') --config $configPath --request-env
exit $LASTEXITCODE
'@
[IO.File]::WriteAllText($dispatcherPath, $dispatcher + "`r`n", $utf8)
$configData = [ordered]@{
    crysis_root = $CrysisRoot; mod_root = $modRoot; python_exe = $pythonExe;
    host_user = $sshUser; client_vpn_address = $ClientVpnAddress; host_vpn_address = $HostVpnAddress;
    authorized_keys_file = $keysFile; key_marker = $keyMarker; client_key_body = $keyBody;
    firewall_rule = 'CrysisCoopBridge-In-TCP'; ssh_port = $sshPort;
}
[IO.File]::WriteAllText($bridgeConfig, ($configData | ConvertTo-Json) + "`r`n", $utf8)
$stopSource = Join-Path $PSScriptRoot 'Stop_Host_Bridge.ps1'
if (Test-Path -LiteralPath $stopSource) { Copy-Item -LiteralPath $stopSource -Destination $bridgeDirectory -Force }
foreach ($protectedFile in @($agentTarget, $dispatcherPath, $bridgeConfig)) { Set-AdminOnlyAcl $protectedFile }

$powershellExe = (Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe').Replace('\', '/')
$forcedCommand = '"' + $powershellExe + '" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $dispatcherPath.Replace('\', '/') + '"'
$forcedCommand = $forcedCommand.Replace('"', '\"')
$keyEntry = 'from="' + $ClientVpnAddress + '",no-agent-forwarding,no-port-forwarding,no-pty,no-X11-forwarding,command="' +
    $forcedCommand + '" ssh-ed25519 ' + $keyBody + ' ' + $keyMarker
New-Item -ItemType Directory -Path (Split-Path $keysFile -Parent) -Force | Out-Null
$existingKeys = @()
if (Test-Path -LiteralPath $keysFile) { $existingKeys = @([IO.File]::ReadAllLines($keysFile)) }
$existingKeys = @($existingKeys | Where-Object { $_ -notmatch ('\s' + [regex]::Escape($keyMarker) + '\s*$') })
[IO.File]::WriteAllLines($keysFile, [string[]]($existingKeys + $keyEntry), $utf8)
Set-AdminOnlyAcl $keysFile

Get-NetFirewallRule -Name 'CrysisCoopBridge-In-TCP' -ErrorAction SilentlyContinue | Remove-NetFirewallRule
New-NetFirewallRule -Name 'CrysisCoopBridge-In-TCP' -DisplayName 'Crysis Co-op development bridge (Radmin peer only)' -Enabled True `
    -Direction Inbound -Protocol TCP -Action Allow -LocalPort $sshPort -LocalAddress $HostVpnAddress -RemoteAddress $ClientVpnAddress `
    -Program $sshdExe -Profile Any | Out-Null
Set-Service -Name sshd -StartupType Automatic
if (-not $hadConfig) {
    # The VPN adapter may become available after SSH during Windows startup.
    & sc.exe failure sshd reset= 86400 actions= restart/10000/restart/30000/restart/60000 | Out-Null
    if ($LASTEXITCODE -ne 0) { Write-Warning 'Could not configure SSH retry after a VPN startup delay.' }
}
Start-Service -Name sshd

$connection = [ordered]@{ host = $HostVpnAddress; user = $sshUser; port = $sshPort; host_public_key = $hostPublicKey; fingerprint = $fingerprint }
[IO.File]::WriteAllText((Join-Path $bridgeDirectory 'connection.json'), ($connection | ConvertTo-Json) + "`r`n", $utf8)
Write-Host ''
Write-Host 'Bridge ready. Send this ONE connection line to your co-developer; it contains no private key or password:'
Write-Output ('BRIDGE_CONNECTION ' + ($connection | ConvertTo-Json -Compress))
Write-Host ('To revoke this bridge: powershell -NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $bridgeDirectory 'Stop_Host_Bridge.ps1') + '"')
