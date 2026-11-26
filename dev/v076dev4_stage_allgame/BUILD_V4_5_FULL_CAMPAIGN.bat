@echo off
setlocal
title Rift Apart Enemy Randomizer - V4.5 deprecated
echo.
echo V4.5 is deprecated because it modifies storymission encounter zones.
echo Launching the V4.6 Story-Safe builder instead.
echo.
call "%~dp0BUILD_V4_6_STORY_SAFE.bat" %*
exit /b %errorlevel%
