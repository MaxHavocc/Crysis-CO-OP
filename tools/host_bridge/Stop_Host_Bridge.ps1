[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this revocation command in PowerShell as Administrator.'
}
$bridgeDirectory = Join-Path $env:ProgramData 'CrysisCoopBridge'
$configPath = Join-Path $bridgeDirectory 'config.json'
if (-not (Test-Path -LiteralPath $configPath)) { throw 'No Crysis Co-op bridge configuration was found.' }
$config = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
$keyFile = [string]$config.authorized_keys_file
if (Test-Path -LiteralPath $keyFile) {
    $remaining = @([IO.File]::ReadAllLines($keyFile) | Where-Object {
        -not ($_ -match ('\s' + [regex]::Escape([string]$config.key_marker) + '\s*$') -and
              $_ -match [regex]::Escape([string]$config.client_key_body))
    })
    [IO.File]::WriteAllLines($keyFile, [string[]]$remaining, (New-Object Text.UTF8Encoding($false)))
}
Get-NetFirewallRule -Name 'CrysisCoopBridge-In-TCP' -ErrorAction SilentlyContinue | Remove-NetFirewallRule
Write-Output 'Crysis Co-op bridge access revoked. Existing requests may finish; new connections with this key are rejected.'
Write-Output 'Other SSH keys, settings, and the SSH service were preserved.'
