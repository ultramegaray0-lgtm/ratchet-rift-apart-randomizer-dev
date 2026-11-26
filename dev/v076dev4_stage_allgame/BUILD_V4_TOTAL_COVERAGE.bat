@echo off
setlocal EnableExtensions
title Rift Apart Enemy Randomizer V4 - Total Coverage Attempt
rem V4 deliberately prioritizes replacing every structurally identifiable regular-enemy spawner.
rem It bypasses faction/movement and spawn-point compatibility for forced factory/node replacements.
rem Story bosses, NPCs, friendlies, mounts, hazards, props, ambiguous nodes and unsafe shared factory variables remain protected.
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
set "OUT=builds\V4_TOTAL_%RANDOM%_%RANDOM%"
echo.
echo ============================================================
echo  RIFT APART ENEMY RANDOMIZER V4 - TOTAL COVERAGE ATTEMPT
echo ============================================================
echo FACTORY ROUTE: forced foreign templates for every structurally valid, single-owner, classifiable regular-enemy factory.
echo NODE ROUTE: exact SpawnerScriptAction Template adapters, local-zone candidates, compatibility bypassed.
echo RETRY ROUTE: .stage data is already randomized when a zone is loaded again; runtime preload runs during loading.
echo RUNTIME: first scene-ready scan, frequent rescan, retry persistence and resident global enemy templates.
echo.
echo IMPORTANT: V4 is intentionally unsafe. Mixed movement/faction and spawn-point rules are bypassed.
echo Some replacements may be unreachable, unkillable, or softlock an encounter. Keep the generated backup.
echo Story bosses, NPCs, friendlies, mounts, hazards, props and ambiguous structures are not treated as regular enemies.
echo.

%PY% -I "tools\stage_enemies\stage_allgame.py" build --game "%GAME%" --out "%OUT%" --seed "RiftApart-Enemy-V4.0" --profile v4 --force-all-enemies --rate 1.0 --no-safe
if errorlevel 1 goto failed

echo.
echo Independently verifying every changed .stage zone against the original game data...
%PY% -I "tools\stage_enemies\stage_allgame.py" check --game "%GAME%" --build "%OUT%"
if errorlevel 1 goto failed

echo.
echo ============================================================
echo V4 BUILD OUTPUTS
echo ============================================================
echo Coverage report: "%OUT%\COVERAGE_REPORT.md"
echo Factory inventory: "%OUT%\inventory.csv"
echo Node inventory: "%OUT%\template_adapter_inventory.csv"
echo Replacement manifest: "%OUT%\stage_enemies_manifest.json"
echo Runtime bundle: "%OUT%\runtime_scripts"
echo Global enemy asset catalog: "%OUT%\15_rando_global_enemy_assets.lua"
echo.
choice /C YN /M "Install V4 now? Every replaced file is backed up first"
if errorlevel 2 goto notnow
%PY% -I "tools\stage_enemies\stage_allgame.py" install --game "%GAME%" --build "%OUT%"
if errorlevel 1 goto failed
> "builds\LAST_INSTALLED.txt" echo %CD%\%OUT%
echo.
echo V4 installed. Enemy Randomizer defaults ON.
echo The resident enemy-template loader now runs during menus and checkpoint loading, not only after scene readiness.
echo Test one checkpoint retry first, then test multiple planets and complete every encounter.
echo Run CHECK_MY_LOG.bat after the session. Do not call coverage 100 percent until the log confirms the spawns.
pause
popd
exit /b 0

:notnow
echo V4 build and byte-level check passed. It was not installed.
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
echo V4 build/check/install failed. If build or check failed, nothing was installed.
pause
popd
exit /b 1
