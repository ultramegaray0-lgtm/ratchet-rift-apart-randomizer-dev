@echo off
setlocal EnableExtensions
title Rift Apart - Hybrid Maximum Local Coverage
rem Aggressive local-zone .stage build + runtime node Template/group adapters.
rem IMPORTANT: no --cross-planet; foreign actor UIDs are not written into target zones.
set "ROOT=%~dp0"
if not exist "%ROOT%tools\stage_enemies\stage_allgame.py" (
  echo ERROR: tools\stage_enemies\stage_allgame.py was not found.
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

set "OUT=builds\HYBRID_MAX_LOCAL_%RANDOM%_%RANDOM%"
if not exist "builds" mkdir "builds"
set "VERD="
if exist "tools\stage_enemies\evidence\verdicts_2026-11-26_015324.json" (
  set "VERD=--verdicts tools\stage_enemies\evidence\verdicts_2026-11-26_015324.json"
)

echo.
echo ============================================================
echo  HYBRID MAXIMUM LOCAL COVERAGE
echo ============================================================
echo .stage: every structurally eligible local-zone factory, including exploratory shared variables.
echo Runtime: node Template/group adapters use the global resident-template registry.
echo Safety: no foreign-zone template UIDs, no arbitrary actors, no direct enemy spawning.
echo The all profile is EXPERIMENTAL: every shared factory variable is eligible.
echo Known failed verdicts, invalid references, non-enemies and unsafe spawn points remain excluded.
echo.

%PY% -I "tools\stage_enemies\stage_allgame.py" build --game "%GAME%" --out "%OUT%" --seed "RiftApart-Hybrid-Max-Local" --profile all --rate 1.0 %VERD%
if errorlevel 1 goto failed

echo.
echo Independently checking the generated .stage against the installed game...
%PY% -I "tools\stage_enemies\stage_allgame.py" check --game "%GAME%" --build "%OUT%"
if errorlevel 1 goto failed

echo.
echo Build report: "%OUT%\COVERAGE_REPORT.md"
echo Per-spawner decisions: "%OUT%\inventory.csv"
echo Global asset catalog: "%OUT%\15_rando_global_enemy_assets.lua"
echo Runtime adapters: "%OUT%\16_rando_spawners.lua"
echo.
choice /C YN /M "Install this aggressive hybrid build now (existing files are backed up first)"
if errorlevel 2 goto notnow
%PY% -I "tools\stage_enemies\stage_allgame.py" install --game "%GAME%" --build "%OUT%"
if errorlevel 1 goto failed
echo.
echo Installed. Keep the Enemy Randomizer ON (press - if needed).
echo The .stage monitor checks factory spawners; runtime adapters cover node Template/group spawners.
echo After testing, run CHECK_MY_LOG.bat so the next build can learn WORKED / NO SPAWN verdicts.
pause
popd
exit /b 0

:notnow
echo Build and check passed; nothing was installed.
pause
popd
exit /b 0

:nopython
echo Python 3 was not found. Install Python 3, then run this again.
pause
popd
exit /b 2

:nogame
echo ERROR: the selected folder must contain RiftApart.exe, toc and dag.
pause
popd
exit /b 2

:failed
echo.
echo Build or independent check failed. Nothing was installed.
pause
popd
exit /b 1
