@echo off
setlocal EnableExtensions
title Rift Apart Enemy Randomizer V2.1 - FORCE ALL ENEMIES

set "ROOT=%~dp0"
if not exist "%ROOT%tools\stage_enemies\stage_allgame.py" (
  echo ERROR: tools\stage_enemies\stage_allgame.py was not found.
  echo Keep this BAT in the complete dev\v076dev4_stage_allgame folder.
  pause
  exit /b 1
)

set "GAME=%~1"
if not defined GAME set /p "GAME=Drag your Rift Apart game folder here, then press Enter: "
set "GAME=%GAME:"=%"
if not exist "%GAME%\RiftApart.exe" (
  echo ERROR: RiftApart.exe not found in %GAME%
  pause
  exit /b 1
)
if not exist "%GAME%\toc" (
  echo ERROR: game toc file not found.
  pause
  exit /b 1
)
if not exist "%GAME%\dag" (
  echo ERROR: game dag file not found.
  pause
  exit /b 1
)

python --version >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python 3 is required.
  pause
  exit /b 1
)

set "OUT=%ROOT%builds\V2.1_FORCE_ALL_%RANDOM%"
if not exist "%ROOT%builds" mkdir "%ROOT%builds"

echo.
echo ============================================================
echo  V2.1 FORCE ALL ENEMIES - EXPERIMENTAL TEST BUILD
echo ============================================================
echo This is the maximum-coverage mode.
echo It tries every classifiable enemy SunsetSpawnerFactory.
echo It can ignore faction, movement, animation clue and shared-owner
echo restrictions. Expect some replacements to fail in-game.
echo It does NOT patch non-enemy Template adapters or malformed
echo multi-Template nodes whose exact meaning is unknown.
echo.
echo The build is checked against your local game before install.
echo Nothing is installed until you explicitly choose Y.
echo.

python -I "%ROOT%tools\stage_enemies\stage_allgame.py" build --game "%GAME%" --out "%OUT%" --seed "RiftApart-V2.1-FORCE-ALL" --profile all --rate 1.0 --force-all-enemies --cross-planet --no-safe
if errorlevel 1 (
  echo.
  echo BUILD FAILED. Nothing was installed. Read the errors above.
  pause
  exit /b 1
)

echo.
echo ============================================================
echo  BUILD COMPLETE
echo ============================================================
echo Output folder:
echo %OUT%
echo.
echo Review COVERAGE_REPORT.md and inventory.csv.
echo The report lists every enemy factory changed and every one
echo that could not be classified or patched.
echo.
set "INSTALL="
set /p "INSTALL=Install this experimental build now? (Y/N): "
if /i not "%INSTALL%"=="Y" goto done

python -I "%ROOT%tools\stage_enemies\stage_allgame.py" install --game "%GAME%" --build "%OUT%"
if errorlevel 1 (
  echo INSTALL FAILED. The build remains in the output folder.
  pause
  exit /b 1
)

:done
echo.
echo V2.1 force-all build is ready for your in-game test.
echo Keep the previous backup. If the game crashes, uninstall/restore it.
pause
