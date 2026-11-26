@echo off
setlocal EnableExtensions
title Rift Apart Enemy Randomizer V4.2 - Campaign Progression Safe
rem V4.2 deliberately leaves every storymission zone native.
rem Non-story zones use the conservative safe planner: same-faction/movement and spawn-point checks.
rem No forced foreign templates, no SpawnerScriptAction Template adapters, no compatibility bypass.
set "ROOT=%~dp0"
if not exist "%ROOT%tools\stage_enemies\stage_allgame.py" (
  echo ERROR: stage_allgame.py was not found.
  pause
  exit /b 1
)
pushd "%ROOT%"
set "PY=py -3"
%PY% --version >nul 2>&1 || set "PY=python"
%PY% --version >nul 2>&1 || goto nopython
set "GAME=%~1"
if not defined GAME set /p "GAME=Drag your Rift Apart game folder here, then press Enter: "
set "GAME=%GAME:"=%"
if not exist "%GAME%\RiftApart.exe" goto nogame
if not exist "%GAME%\toc" goto nogame
if not exist "%GAME%\dag" goto nogame

if not exist "builds" mkdir "builds"
set "OUT=builds\V4_2_CAMPAIGN_SAFE_%RANDOM%_%RANDOM%"
echo.
echo ============================================================
echo  RIFT APART ENEMY RANDOMIZER V4.2 - CAMPAIGN PROGRESSION SAFE
echo ============================================================
echo STORY SAFETY: every levels/.../storymission/... zone stays byte-for-byte native.
echo FACTORIES: conservative safe profile only; same faction/movement and spawn-point checks.
echo NODE ADAPTERS: disabled. Forced foreign templates: disabled.
echo EMERGENCY KEY: F12 (F10 remains reserved for the story-mission test tools).
echo.
echo This is a campaign-safety build, not a 100-percent enemy replacement build.
echo It is designed to isolate whether storymission stage edits caused the progression blocker.
echo.

%PY% -I "tools\stage_enemies\stage_allgame.py" build --game "%GAME%" --out "%OUT%" --seed "RiftApart-Enemy-V4.2-CampaignSafe" --profile safe --exclude-storymission --rate 1.0 --no-safe
if errorlevel 1 goto failed

echo.
echo Independently verifying every changed .stage zone against the original game data...
%PY% -I "tools\stage_enemies\stage_allgame.py" check --game "%GAME%" --build "%OUT%"
if errorlevel 1 goto failed

echo.
echo ============================================================
echo V4.2 BUILD OUTPUTS
echo ============================================================
echo Coverage report: "%OUT%\COVERAGE_REPORT.md"
echo Factory inventory: "%OUT%\inventory.csv"
echo Node inventory: "%OUT%\template_adapter_inventory.csv"
echo Replacement manifest: "%OUT%\stage_enemies_manifest.json"
echo Runtime bundle: "%OUT%\runtime_scripts"
echo.
choice /C YN /M "Install V4.2 now? Every replaced file is backed up first"
if errorlevel 2 goto notnow
%PY% -I "tools\stage_enemies\stage_allgame.py" install --game "%GAME%" --build "%OUT%"
if errorlevel 1 goto failed
> "builds\LAST_INSTALLED.txt" echo %CD%\%OUT%
echo.
echo V4.2 installed. Storymission zones are native; only non-story zones are randomized.
echo Emergency recovery is F12, not F10.
echo Reload the current checkpoint after installation before testing progression.
pause
popd
exit /b 0

:notnow
echo V4.2 build and byte-level check passed. It was not installed.
pause
popd
exit /b 0

:nopython
echo Python 3 was not found. Install Python 3, then run this again.
pause
popd
exit /b 2

:nogame
echo ERROR: selected folder must contain RiftApart.exe, toc and dag.
pause
popd
exit /b 2

:failed
echo.
echo V4.2 build/check/install failed. If build or check failed, nothing was installed.
pause
popd
exit /b 1
