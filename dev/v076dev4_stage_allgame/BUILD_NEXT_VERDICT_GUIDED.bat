@echo off
setlocal EnableExtensions
rem Rift Apart Enemy Randomizer V3.0 - evidence-guided hybrid build.
rem Locate the project root from this BAT, not from the game folder/current directory.
set "ROOT=%~dp0"
for /L %%N in (1,1,7) do (
  if exist "%ROOT%tools\stage_enemies\stage_allgame.py" goto rootfound
  for %%I in ("%ROOT%..") do set "ROOT=%%~fI\"
)
:rootfound
if not exist "%ROOT%tools\stage_enemies\stage_allgame.py" goto missingtools
pushd "%ROOT%"
set "PY=python"
%PY% --version >nul 2>&1 || set "PY=py -3"
%PY% --version >nul 2>&1 || goto nopython
set "GAME=%~1"
if not defined GAME set /p "GAME=Drag your Rift Apart game folder here and press Enter: "
if not defined GAME goto nogame
set "GAME=%GAME:"=%"
if not exist "%GAME%\RiftApart.exe" goto nogame
if not exist "%GAME%\toc" goto nogame
%PY% -c "import lz4.block" >nul 2>&1 || echo Tip: "pip install lz4" is free and makes the scan much faster.
set "VERD="
if exist "verdicts\*.json" for %%f in ("verdicts\*.json") do call set "VERD=%%VERD%% --verdicts "%%~ff""
if not defined VERD echo WARNING: no verdict JSON found. Run CHECK_MY_LOG.bat first if you want previous test results applied.
echo.
echo Building the evidence-guided V3.0 hybrid profile for every readable planet...
echo .stage references stay local; global resident templates feed the runtime node/factory adapters. Cross-planet UIDs are DISABLED.
echo Known ORIGINAL SPAWNED and NO SPAWN results will be left unchanged.
%PY% -I "tools\stage_enemies\stage_allgame.py" build --game "%GAME%" --out "builds\AUTO" --profile v3 --rate 1.0 %VERD%
if errorlevel 1 goto failed
set /p OUT=<"builds\LAST_BUILD.txt"
echo.
echo Build report: "%OUT%\COVERAGE_REPORT.md"
echo Per-spawner decisions: "%OUT%\inventory.csv"
echo Replacement manifest: "%OUT%\stage_enemies_manifest.json"
echo.
choice /C YN /M "Install this evidence-guided build now (current files are backed up first)"
if errorlevel 2 goto notnow
%PY% -I "tools\stage_enemies\stage_allgame.py" install --game "%GAME%" --build "%OUT%"
if errorlevel 1 goto failed
copy /y "builds\LAST_BUILD.txt" "builds\LAST_INSTALLED.txt" >nul
echo.
echo V3.0 evidence-guided build installed. Enable Enemy Randomizer with - before entering a level.
echo CHECK_MY_LOG.bat now records factory and node Template verdicts for every shared owner key.
pause
popd
exit /b 0
:missingtools
echo ERROR: Could not find tools\stage_enemies\stage_allgame.py in this folder or its 7 parent folders.
echo Download and extract the complete project ZIP, then run this BAT from inside dev\v076dev4_stage_allgame.
pause
exit /b 3
:nopython
echo Python 3 was not found. Install it from python.org (free), tick Add python.exe to PATH, then run this again.
pause
popd
exit /b 2
:nogame
echo That is not the game folder: it must hold RiftApart.exe and toc.
pause
popd
exit /b 2
:failed
echo.
echo Build or installation failed. Nothing was installed if the build/check step failed.
pause
popd
exit /b 1
