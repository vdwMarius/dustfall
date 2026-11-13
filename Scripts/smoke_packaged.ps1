param([ValidateSet('Phase3','Phase4')][string]$Phase = 'Phase4')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$packageRoot = Join-Path $projectRoot "Builds\$Phase\Windows"
$gameFile = Join-Path $packageRoot 'dustfall.exe'
if (-not (Test-Path -LiteralPath $gameFile)) { throw "Package absent: $gameFile" }
$qaRoot = Join-Path $projectRoot "Saved\Codex\PackagedSmoke\$Phase"
New-Item -ItemType Directory -Path $qaRoot -Force | Out-Null
$smokeLog = Join-Path $qaRoot 'smoke.log'
# A short capture provides automatic clean exit. This is a startup smoke,
# deliberately not a performance benchmark or traversal/regression test.
$gameArguments = @('-windowed','-ResX=1920','-ResY=1080','-ForceRes','-NoVSync',
    '-nosplash','-unattended',"-UserDir=`"$qaRoot`"", "-abslog=`"$smokeLog`"",
    '-ExecCmds="t.MaxFPS 60,r.VSync 0,r.ScreenPercentage 100,r.DynamicRes.OperationMode 0,sg.ViewDistanceQuality 2,sg.AntiAliasingQuality 2,sg.ShadowQuality 2,sg.GlobalIlluminationQuality 2,sg.ReflectionQuality 2,sg.PostProcessQuality 2,sg.TextureQuality 2,sg.EffectsQuality 2,sg.FoliageQuality 2,sg.ShadingQuality 2,csvprofile exitoncompletion,csvprofile frames=600"')
$smokeProcess = Start-Process -FilePath $gameFile -ArgumentList $gameArguments -WorkingDirectory $packageRoot -WindowStyle Hidden -PassThru
Write-Host "Started $Phase brief packaged smoke, PID $($smokeProcess.Id), isolated user data: $qaRoot"
$smokeProcess.WaitForExit()
$smokeContent = Get-Content -LiteralPath $smokeLog -Raw
$errorsFound = [regex]::Matches($smokeContent,'(?im)^.*(?:Error:|Fatal error|Assertion failed|Ensure condition failed|Accessed None).*$') | ForEach-Object { $_.Value }
$report = [ordered]@{
    phase=$Phase
    exit_code=$smokeProcess.ExitCode
    log=$smokeLog
    isolated_user_directory=$qaRoot
    loaded_foundation_map=($smokeContent -match 'Bringing World /Game/World/Maps/L_Dustfall_Foundation')
    clean_exit=($smokeContent -match 'LogExit: Exiting')
    errors=@($errorsFound)
    scope='600-frame stationary packaged startup smoke only. User requested heavy tests deferred; no traversal, restart-persistence, visual acceptance or performance certification.'
}
$report.status = if ($report.exit_code -eq 0 -and $report.loaded_foundation_map -and $report.clean_exit -and $report.errors.Count -eq 0) { 'passed' } else { 'failed' }
$report | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $qaRoot 'result.json') -Encoding utf8
$report | ConvertTo-Json -Depth 4
if ($report.status -ne 'passed') { throw 'Packaged startup smoke failed; inspect its log and report.' }
