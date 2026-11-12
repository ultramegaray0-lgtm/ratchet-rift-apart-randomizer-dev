@echo off
rem READ-ONLY: copies a few game functions out of the running game for randomizer research.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Dump-GameCode.ps1"
pause
