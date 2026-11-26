@echo off
setlocal EnableExtensions
title Rift Apart Enemy Randomizer V3.0 - Maximum Coverage
rem V3.0 experimental hybrid: .stage factories + exact SpawnerScriptAction Template nodes.
rem Local-zone only. No foreign actor UID references and no direct combat actor spawning.
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

if not exist "builds" mkdir "builds"
set "OUT=builds\V3_0_MAX_%RANDOM%_%RANDOM%"
set "VERD="
if exist "tools\stage_enemies\evidence\verdicts_2026-11-26_015324.json" (
  set "VERD=--verdicts tools\stage_enemies\evidence\verdicts_2026-11-26_015324.json"
)

echo.
echo ============================================================
echo  RIFT APART ENEMY RANDOMIZER V3.0 - MAX COVERAGE
echo ============================================================
echo FACTORY ROUTE: .stage SunsetSpawnerFactory Templates variables.
echo NODE ROUTE: exact SpawnerScriptAction nodes with one local Template plug.
echo RUNTIME FALLBACK: unpatched factory, node Template and group adapters can use local/global resident templates.
echo SAFETY: no foreign-zone actor UID references, no arbitrary actor promotion, no direct combat spawning.
echo SHARED VARIABLES: only verified all-spawner node Template groups are patched; ambiguous shared factory/node variables stay native.
echo NODE ADAPTERS: single-owner and safe shared-owner groups; one shared variable is patched once for every unique spawner owner.
echo PAIRS: proven + same-faction/same-movement kin; known failed pairs stay excluded.
echo A SAFE factory-only fallback is built alongside V3.
echo.

%PY% -I "tools\stage_enemies\stage_allgame.py" build --game "%GAME%" --out "%OUT%" --seed "RiftApart-Enemy-V3.0" --profile v3 --rate 1.0 %VERD%
if errorlevel 1 goto failed

echo.
echo Independently verifying the V3 .stage against the original game zones...
%PY% -I "tools\stage_enemies\stage_allgame.py" check --game "%GAME%" --build "%OUT%"
if errorlevel 1 goto failed

echo.
echo ============================================================
echo V3.0 OUTPUTS
echo ============================================================
echo V3 report: "%OUT%\COVERAGE_REPORT.md"
echo Factory inventory: "%OUT%\inventory.csv"
echo Node adapter inventory: "%OUT%\template_adapter_inventory.csv"
echo Runtime bundle: "%OUT%\runtime_scripts"
echo Global asset catalog: "%OUT%\15_rando_global_enemy_assets.lua"
echo Safe fallback: "%OUT%\safe"
echo.
choice /C YN /M "Install V3.0 now? All replaced scripts are backed up first"
if errorlevel 2 goto notnow
%PY% -I "tools\stage_enemies\stage_allgame.py" install --game "%GAME%" --build "%OUT%"
if errorlevel 1 goto failed
> "builds\LAST_INSTALLED.txt" echo %CD%\%OUT%
echo.
echo V3.0 installed. The installer synchronized the complete 10.0.51 script kit.
echo The installed build path was saved so CHECK_MY_LOG.bat can read this exact manifest.
echo Turn the Enemy Randomizer ON with - BEFORE entering a level; global templates warm up while it is enabled.
echo Test several planets and complete full encounters before treating coverage as proven.
echo Run CHECK_MY_LOG.bat after testing to produce the next evidence update.
pause
popd
exit /b 0

:notnow
echo Build and independent check passed; nothing was installed.
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
echo Build or independent verification failed. Nothing was installed.
pause
popd
exit /b 1
