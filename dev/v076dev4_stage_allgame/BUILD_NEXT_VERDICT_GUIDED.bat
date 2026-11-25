@echo off
setlocal EnableExtensions
rem Rift Apart Randomizer v0.76-DEV4 - evidence-guided all-planet build.
rem Uses the game's local templates only; does NOT use experimental cross-planet Template references.
rem Imports all verdict JSON files from verdicts\ so known failures stay native and known successes are pinned.
cd /d "%~dp0"
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
echo Building the evidence-guided MAX profile for every readable planet...
echo Local-zone enemy templates only. Cross-planet template references are DISABLED.
echo Known ORIGINAL SPAWNED and NO SPAWN results will be left unchanged.
%PY% -I "tools\stage_enemies\stage_allgame.py" build --game "%GAME%" --out "builds\NEXT" --profile max --rate 1.0 %VERD%
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
echo Installed. Keep Enemy Randomizer ON (press - if needed) while testing.
echo Run CHECK_MY_LOG.bat after playing to improve the next build.
pause
exit /b 0
:notnow
echo Not installed. You can install later with:
echo %PY% -I tools\stage_enemies\stage_allgame.py install --game "%GAME%" --build "%OUT%"
pause
exit /b 0
:nopython
echo Python 3 was not found. Install it from python.org (free), tick Add python.exe to PATH, then run this again.
pause
exit /b 2
:nogame
echo That is not the game folder: it must hold RiftApart.exe and toc.
pause
exit /b 2
:failed
echo.
echo Build or installation failed. Nothing was installed if the build/check step failed.
pause
exit /b 1
