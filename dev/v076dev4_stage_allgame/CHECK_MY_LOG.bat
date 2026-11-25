@echo off
setlocal EnableExtensions
rem Reads your rivet.log: per changed spawner WORKED / ORIGINAL SPAWNED / NO SPAWN / NOT REACHED, totals per planet.
rem Keeps a copy of the log, the report and verdicts-<time>.json in verdicts\ ; the next BUILD_ALL_PLANETS.bat reads every
rem verdicts file: what WORKED is kept, ORIGINAL SPAWNED / NO SPAWN spawners stay native.
rem usage: CHECK_MY_LOG.bat ["C:\path\to\game folder"]
cd /d "%~dp0"
set "PY=python"
%PY% --version >nul 2>&1 || set "PY=py -3"
set "GAME=%~1"
if not defined GAME set /p "GAME=Drag your Rift Apart game folder here and press Enter: "
if not defined GAME goto nolog
set "GAME=%GAME:"=%"
if not exist "%GAME%\rivet.log" goto nolog
if not exist "builds\LAST_INSTALLED.txt" goto nobuild
set /p BUILD=<"builds\LAST_INSTALLED.txt"
%PY% -I "tools\stage_enemies\stage_check_log.py" "%GAME%\rivet.log" --manifest "%BUILD%\stage_enemies_manifest.json" --save-dir "verdicts" > "verdicts_last_check.txt"
more < "verdicts_last_check.txt"
pause
exit /b 0
:nolog
echo No rivet.log in that folder: play first, then run this.
pause
exit /b 2
:nobuild
echo No build was installed with BUILD_ALL_PLANETS.bat yet.
pause
exit /b 2