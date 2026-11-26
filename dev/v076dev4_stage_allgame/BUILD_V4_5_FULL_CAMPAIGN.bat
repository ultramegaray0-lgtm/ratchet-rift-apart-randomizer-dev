@echo off
setlocal EnableExtensions
title Rift Apart Enemy Randomizer V4.5 - Full Campaign Experimental
rem V4.5 uses the builder's maximum-coverage V4 profile. Storymission zones are INCLUDED.
rem This is intentionally unsafe: it bypasses movement/faction and spawn-point compatibility checks.
rem Ambiguous/shared-owner templates, bosses and non-regular actors remain protected by structural/classification gates.
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
set "OUT=builds\V4_5_FULL_CAMPAIGN_%RANDOM%_%RANDOM%"
echo.
echo ============================================================
echo  RIFT APART ENEMY RANDOMIZER V4.5 - FULL CAMPAIGN EXPERIMENTAL
echo ============================================================
echo STORYMISSION ZONES: INCLUDED
echo COVERAGE: maximum V4 profile, all eligible classifiable regular-enemy factories
echo CROSS-ZONE POOL: enabled by V4 global actor catalogue and foreign UID references
echo COMPATIBILITY: faction/movement and spawn-point checks bypassed (UNSAFE)
echo RATE: 100 percent of eligible candidates
echo.
echo IMPORTANT:
echo - This is a maximum-coverage experiment, not a verified 100%% replacement.
echo - Shared/ambiguous variables and non-regular or unclassified actors remain excluded.
echo - Foreign template references can fail to spawn or become unkillable.
echo - V now tracks the live mission callback and attempts a verified active-state recovery when helper v6 supports it; it never claims an encounter output was fired.
echo - F11 is emergency recovery. It cannot repair an already stuck mission objective.
echo.
choice /C YN /M "Build V4.5 including story mission encounters? This is experimental"
if errorlevel 2 goto cancelled

%PY% -I "tools\stage_enemies\stage_allgame.py" build --game "%GAME%" --out "%OUT%" --seed "RiftApart-Enemy-V4.5-FullCampaign" --profile v4 --force-all-enemies --rate 1.0
if errorlevel 1 goto failed

echo.
echo Independently verifying every changed .stage zone against the original game data...
%PY% -I "tools\stage_enemies\stage_allgame.py" check --game "%GAME%" --build "%OUT%"
if errorlevel 1 goto failed

echo.
echo ============================================================
echo V4.5 BUILD OUTPUTS
echo ============================================================
echo Main experimental coverage report: "%OUT%\COVERAGE_REPORT.md"
echo Factory inventory: "%OUT%\inventory.csv"
echo Node inventory: "%OUT%\template_adapter_inventory.csv"
echo Replacement manifest: "%OUT%\stage_enemies_manifest.json"
echo Runtime bundle: "%OUT%\runtime_scripts"
if exist "%OUT%\safe\COVERAGE_REPORT.md" echo Conservative fallback report: "%OUT%\safe\COVERAGE_REPORT.md"
echo.
choice /C YN /M "Install V4.5 now? The installer backs up every replaced file"
if errorlevel 2 goto notnow
%PY% -I "tools\stage_enemies\stage_allgame.py" install --game "%GAME%" --build "%OUT%"
if errorlevel 1 goto failed
> "builds\LAST_INSTALLED.txt" echo %CD%\%OUT%
echo.
echo V4.5 installed. Reload from a NEW GAME / new campaign start for a clean test.
echo Keep the generated manifest and coverage report.
echo V = mission recovery attempt; it verifies the live mission state before completing cleanup. Encounter door/wave outputs remain game-owned.\necho F11 = emergency enemy recovery.
pause
popd
exit /b 0

:cancelled
echo Build cancelled. No game files changed.
pause
popd
exit /b 0

:notnow
echo V4.5 build and byte-level check passed. It was not installed.
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
echo V4.5 build/check/install failed. If build or check failed, installation was not performed.
pause
popd
exit /b 1
