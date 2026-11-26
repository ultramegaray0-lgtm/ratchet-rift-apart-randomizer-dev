@echo off
setlocal EnableExtensions
rem Read-only scan for Template adapter candidates. Does NOT build or install a mod.
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
if not exist "%GAME%\dag" goto nogame
set "OUT=adapter_scan_%RANDOM%"
echo.
echo READ-ONLY scan. No game files will be changed.
echo Output: "%OUT%"
echo.
%PY% -I "tools\stage_enemies\stage_allgame.py" scan --game "%GAME%" --out "%OUT%"
if errorlevel 1 goto failed
echo.
echo DONE. Upload this file from "%OUT%":
echo   template_adapter_inventory.csv
echo Also upload:
echo   COVERAGE_REPORT.md
echo   inventory.csv
echo.
pause
exit /b 0
:nopython
echo Python 3 was not found. Install Python 3, then run again.
pause
exit /b 2
:nogame
echo Select the game folder containing RiftApart.exe, toc and dag.
pause
exit /b 2
:failed
echo Scan failed. No game files were changed. Read the error above.
pause
exit /b 1
