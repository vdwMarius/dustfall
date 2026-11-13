param([string]$EngineRoot = 'G:\Program Files\UE_5.8')
$ErrorActionPreference = 'Stop'
$phase3Archive = Join-Path (Split-Path -Parent $PSScriptRoot) 'Builds\Phase3'
& (Join-Path $PSScriptRoot 'package_phase2.ps1') -EngineRoot $EngineRoot -ArchiveDirectory $phase3Archive
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'Play_Phase3.cmd') -Destination (Join-Path $phase3Archive 'Windows\Play_DUSTFALL.cmd') -Force
Write-Host "Phase 3 Windows build: $phase3Archive\Windows\Play_DUSTFALL.cmd"
