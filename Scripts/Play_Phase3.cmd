@echo off
setlocal
rem Copied beside dustfall.exe by package_phase3.ps1.
if not exist "%~dp0dustfall.exe" (
  echo Run Builds\Phase3\Windows\Play_DUSTFALL.cmd after packaging.
  pause
  exit /b 1
)
start "DUSTFALL Phase 3" /D "%~dp0" "%~dp0dustfall.exe" -windowed -ResX=1920 -ResY=1080 -ForceRes -NoVSync -ExecCmds="t.MaxFPS 0,r.VSync 0,r.ScreenPercentage 100,r.DynamicRes.OperationMode 0,sg.ViewDistanceQuality 2,sg.AntiAliasingQuality 2,sg.ShadowQuality 2,sg.GlobalIlluminationQuality 2,sg.ReflectionQuality 2,sg.PostProcessQuality 2,sg.TextureQuality 2,sg.EffectsQuality 2,sg.FoliageQuality 2,sg.ShadingQuality 2"
