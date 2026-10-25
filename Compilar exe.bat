@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Compilar Bubblepad
if not exist ".venv\Scripts\python.exe" (echo Abre primero / run first "Iniciar Bubblepad.bat" & pause & exit /b)
echo.
echo  Compilando Bubblepad.exe (unos minutos)... / Building Bubblepad.exe (a few minutes)...
echo.
".venv\Scripts\python.exe" -m pip install -q pyinstaller || (echo Fallo instalando PyInstaller & pause & exit /b)
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --windowed --name Bubblepad ^
  --icon assets\bubblepad.ico ^
  --add-data "ui;ui" --add-data "assets;assets" --add-data "demo_sounds;demo_sounds" ^
  bubblepad.py || (echo Fallo al compilar & pause & exit /b)
powershell -NoProfile -Command "Compress-Archive -Path 'dist\Bubblepad' -DestinationPath 'dist\Bubblepad-windows.zip' -Force"
echo.
echo  Listo / Done:
echo    dist\Bubblepad\Bubblepad.exe
echo    dist\Bubblepad-windows.zip  (para compartir / to share)
explorer dist
pause
