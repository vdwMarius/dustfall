param([string]$EngineRoot = 'G:\Program Files\UE_5.8')
$ErrorActionPreference = 'Stop'
$phase4Archive = Join-Path (Split-Path -Parent $PSScriptRoot) 'Builds\Phase4'
& (Join-Path $PSScriptRoot 'package_phase2.ps1') -EngineRoot $EngineRoot -ArchiveDirectory $phase4Archive
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'Play_Phase4.cmd') -Destination (Join-Path $phase4Archive 'Windows\Play_DUSTFALL.cmd') -Force
Write-Host "Phase 4 Windows build: $phase4Archive\Windows\Play_DUSTFALL.cmd"
