param(
    [string]$EngineRoot = 'G:\Program Files\UE_5.8',
    [string]$ArchiveDirectory = ''
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $ArchiveDirectory) { $ArchiveDirectory = Join-Path $projectRoot 'Builds\Phase2' }
$projectFile = Join-Path $projectRoot 'dustfall.uproject'
$runUat = Join-Path $EngineRoot 'Engine\Build\BatchFiles\RunUAT.bat'
$editorCommandlet = Join-Path $EngineRoot 'Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
if (-not (Test-Path -LiteralPath $runUat)) { throw "Unreal AutomationTool not found: $runUat" }
if (-not (Test-Path -LiteralPath $projectFile)) { throw "Project not found: $projectFile" }
$buildArguments = @(
    'BuildCookRun', "-project=$projectFile", '-nop4', '-platform=Win64',
    '-clientconfig=Development', '-build', '-cook', "-unrealexe=$editorCommandlet",
    '-map=/Game/World/Maps/L_Dustfall_Foundation', '-stage', '-pak', '-package',
    '-archive', "-archivedirectory=$ArchiveDirectory", '-nocompileeditor',
    '-installed', '-utf8output', '-unattended'
)
& $runUat @buildArguments
if ($LASTEXITCODE -ne 0) { throw "BuildCookRun failed with exit code $LASTEXITCODE" }
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'Play_Phase2.cmd') -Destination (Join-Path $ArchiveDirectory 'Windows\Play_DUSTFALL.cmd') -Force
Write-Host "Windows build: $ArchiveDirectory\Windows\dustfall.exe"
