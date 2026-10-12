@echo off
chcp 65001 >nul
title AICADBridge — SolidWorks & Adam-CAD Studio
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py solidworks_server.py %*
) else (
    python solidworks_server.py %*
)
pause
