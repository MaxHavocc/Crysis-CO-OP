param(
    [string]$CrysisRoot = (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
)

$ErrorActionPreference = 'Stop'
# C1-Launcher supports mod DLLs and direct connections without GameSpy.
# Keep the original game executable; install the x86 runtime beside it.
$releaseUrl = 'https://github.com/ccomrade/c1-launcher/releases/download/v8/c1-launcher-v8-build.zip'
$releaseHash = 'a61c631b990b46dac67f47407b7e5906d82fcabfdd8e64478d05bc51d61b08fa'
$binDir = Join-Path $CrysisRoot 'Bin32'
if (-not (Test-Path -LiteralPath (Join-Path $binDir 'CrySystem.dll'))) {
    throw 'Crysis Bin32 was not found. Pass -CrysisRoot with your Crysis installation path.'
}
$target = Join-Path $binDir 'CrysisCoop.exe'
$tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
$staging = Join-Path $tempRoot ('crysis-coop-runtime-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $staging | Out-Null
try {
    $archive = Join-Path $staging 'c1-launcher-v8.zip'
    Invoke-WebRequest -Uri $releaseUrl -OutFile $archive -UseBasicParsing -TimeoutSec 60
    if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash -ne $releaseHash) {
        throw 'C1 launcher download failed SHA-256 verification. Nothing was installed.'
    }
    Expand-Archive -LiteralPath $archive -DestinationPath (Join-Path $staging 'extracted')
    $source = Join-Path $staging 'extracted\Crysis\Bin32\Crysis.exe'
    $sourceHash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
    if (Test-Path -LiteralPath $target) {
        if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -eq $sourceHash) {
            Write-Output 'Crysis Co-op runtime is already installed and verified.'
            return
        }
        # Preserve an existing alternate runtime before replacing it.
        $backup = $target + '.' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.bak'
        Copy-Item -LiteralPath $target -Destination $backup -ErrorAction Stop
    }
    Copy-Item -LiteralPath $source -Destination $target -Force
    if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ne $sourceHash) {
        throw 'Installed runtime failed verification.'
    }
    Write-Output ('Installed C1-Launcher v8 for co-op: ' + $target)
    Write-Output 'The original Bin32\Crysis.exe was preserved.'
}
finally {
    $resolvedStaging = [IO.Path]::GetFullPath($staging)
    if ($resolvedStaging.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase) -and
        (Split-Path $resolvedStaging -Leaf) -match '^crysis-coop-runtime-[0-9a-f]{32}$') {
        Remove-Item -LiteralPath $resolvedStaging -Recurse -Force
    }
}
