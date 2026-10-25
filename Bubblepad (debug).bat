@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Bubblepad (debug)
if not exist ".venv\Scripts\python.exe" (echo Abre primero / run first "Iniciar Bubblepad.bat" & pause & exit /b)
".venv\Scripts\python.exe" bubblepad.py
pause
