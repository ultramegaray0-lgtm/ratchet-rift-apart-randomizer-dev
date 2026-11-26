@echo off
setlocal EnableExtensions
title Rift Apart Enemy Randomizer V2.0 MAX

rem This launcher lives beside tools\ and scripts\ in the v076dev4_stage_allgame folder.
set "ROOT=%~dp0"
if not exist "%ROOT%tools\stage_enemies\stage_allgame.py" (
  echo ERROR: tools\stage_enemies\stage_allgame.py was not found beside this launcher.
  echo Keep BUILD_V2_MAX.bat inside the complete v076dev4_stage_allgame folder.
  pause
  exit /b 1
)

set "GAME=%~1"
if not defined GAME set /p "GAME=Drag your Rift Apart game folder here, then press Enter: "
set "GAME=%GAME:"=%"
if not exist "%GAME%\RiftApart.exe" (
  echo ERROR: RiftApart.exe was not found in:
  echo %GAME%
  pause
  exit /b 1
)
if not exist "%GAME%\toc" (
  echo ERROR: the game's toc file was not found.
  pause
  exit /b 1
)
if not exist "%GAME%\dag" (
  echo ERROR: the game's dag file was not found.
  pause
  exit /b 1
)

set "PY=python"
%PY% --version >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python 3 is required.
  pause
  exit /b 1
)

set "TAG=%RANDOM%"
set "LOCAL=%ROOT%builds\V2.0_LOCAL_MAX_%TAG%"
set "CROSS=%ROOT%builds\V2.0_CROSS_PLANET_MAX_%TAG%"
if not exist "%ROOT%builds" mkdir "%ROOT%builds"

echo.
echo ============================================================
echo  ENEMY RANDOMIZER V2.0 - MAXIMUM EVIDENCE-GUIDED BUILD
echo ============================================================
echo Latest 2026-11-26 verdicts are bundled automatically.
echo  WORKED: exact runtime replacement is pinned.
echo  NO SPAWN / ORIGINAL SPAWNED: that spawner stays native.
echo  NOT REACHED: remains eligible for the expanded shuffle.
echo.
echo Build A: MAX local-zone templates (recommended fallback).
echo Build B: MAX cross-planet templates (EXPERIMENTAL; unproven).
echo Both builds are separate. Nothing is installed until you choose.
echo.

echo [1/4] Building local-zone MAX...
%PY% -I "%ROOT%tools\stage_enemies\stage_allgame.py" build --game "%GAME%" --out "%LOCAL%" --seed "RiftApart-Enemy-V2.0-MAX" --profile max --rate 1.0 --no-safe
if errorlevel 1 (
  echo ERROR: local MAX build failed. See the output above.
  pause
  exit /b 1
)
echo [2/4] Verifying local-zone MAX...
%PY% -I "%ROOT%tools\stage_enemies\stage_allgame.py" check --game "%GAME%" --build "%LOCAL%"
if errorlevel 1 (
  echo ERROR: local MAX build did not pass its independent check.
  pause
  exit /b 1
)

echo.
echo [3/4] Building CROSS-PLANET MAX (experimental)...
%PY% -I "%ROOT%tools\stage_enemies\stage_allgame.py" build --game "%GAME%" --out "%CROSS%" --seed "RiftApart-Enemy-V2.0-CROSS-MAX" --profile max --rate 1.0 --cross-planet --no-safe
if errorlevel 1 (
  echo WARNING: cross-planet build failed. The verified local-zone build is still available.
  set "CROSS="
) else (
  echo [4/4] Verifying CROSS-PLANET MAX...
  %PY% -I "%ROOT%tools\stage_enemies\stage_allgame.py" check --game "%GAME%" --build "%CROSS%"
  if errorlevel 1 (
    echo WARNING: cross-planet build failed its check and will not be offered for install.
    set "CROSS="
  )
)

echo.
echo ============================================================
echo BUILD OUTPUTS
echo ============================================================
echo Local MAX:
echo %LOCAL%
if defined CROSS (
  echo.
  echo Cross-planet MAX - EXPERIMENTAL:
  echo %CROSS%
)
echo.
echo The latest evidence file is included in the tools evidence folder.
echo Each build includes its own .stage, Lua manifest, inventory,
echo template-adapter census, coverage report and JSON manifest.
echo.

:choose
echo Install which build?
echo   L = local-zone MAX (recommended)
if defined CROSS echo   X = cross-planet MAX (experimental)
echo   N = do not install yet
set "CHOICE="
set /p "CHOICE=Choose L, X or N: "
if /i "%CHOICE%"=="N" goto done
if /i "%CHOICE%"=="L" (
  %PY% -I "%ROOT%tools\stage_enemies\stage_allgame.py" install --game "%GAME%" --build "%LOCAL%"
  goto done
)
if /i "%CHOICE%"=="X" if defined CROSS (
  echo WARNING: this build uses foreign-zone template UIDs via idx=0xFFFF.
  echo It passed the byte-level checker, but engine acceptance is NOT yet proven.
  %PY% -I "%ROOT%tools\stage_enemies\stage_allgame.py" install --game "%GAME%" --build "%CROSS%"
  goto done
)
echo Invalid choice.
goto choose

:done
echo.
echo Finished. Your previous installed files were backed up before replacement.
pause
