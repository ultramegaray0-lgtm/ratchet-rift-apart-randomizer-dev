@echo off
setlocal EnableExtensions
rem Rift Apart Randomizer v0.76-DEV4 - all-planet .stage Enemy Randomizer (stage_allgame 2.0.0)
rem Scans EVERY zone of your game (read-only), builds RandoEnemies.stage + its manifest in builds\build-<time>,
rem checks it against your game files, then offers to install it (the files it replaces are backed up first).
rem usage: BUILD_ALL_PLANETS.bat ["C:\path\to\game folder"] [extra options, e.g. --profile safe]
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
%PY% -c "import lz4.block" >nul 2>&1 || echo Tip: "pip install lz4" (free) makes the scan about 100x faster. Without it the scan takes several minutes.
set "VERD="
if exist "verdicts\*.json" for %%f in ("verdicts\*.json") do call set "VERD=%%VERD%% --verdicts "%%~ff""
echo.
echo Scanning every zone of "%GAME%" ...
%PY% -I "tools\stage_enemies\stage_allgame.py" build --game "%GAME%" --out "builds\AUTO" --profile all --cross-planet --rate 1.0 %VERD% %2 %3 %4 %5 %6 %7 %8 %9
if errorlevel 1 goto failed
set /p OUT=<"builds\LAST_BUILD.txt"
echo.
echo Report: "%OUT%\COVERAGE_REPORT.md"
echo Every spawner of the game and why: "%OUT%\inventory.csv"
echo A fallback with single-owner spawners (foreign refs remain experimental): "%OUT%\safe"
echo.
choice /C YN /M "Install the main build now (your current files are backed up first)"
if errorlevel 2 goto notnow
%PY% -I "tools\stage_enemies\stage_allgame.py" install --game "%GAME%" --build "%OUT%"
if errorlevel 1 goto failed
copy /y "builds\LAST_BUILD.txt" "builds\LAST_INSTALLED.txt" >nul
echo.
echo Installed. In game keep the Enemy Randomizer ON (the - key) so the log can check each changed spawner.
echo After playing, run CHECK_MY_LOG.bat.
pause
exit /b 0
:notnow
echo Not installed. Later: %PY% -I tools\stage_enemies\stage_allgame.py install --game "%GAME%" --build "%OUT%"
pause
exit /b 0
:nopython
echo Python 3 was not found. Install it from python.org (free), tick "Add python.exe to PATH", then run this again.
pause
exit /b 2
:nogame
echo That is not the game folder: it must hold RiftApart.exe and the toc file.
pause
exit /b 2
:failed
echo.
echo Refused or failed: nothing was installed. See the lines above.
pause
exit /b 1