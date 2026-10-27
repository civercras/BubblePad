@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Bubblepad

if exist ".venv\Scripts\pythonw.exe" goto run

echo.
echo  Primera vez: preparando Bubblepad (tarda un par de minutos, solo esta vez)...
echo  First run: setting up Bubblepad (takes a couple of minutes, only once)...
echo.
set PY=
py -3.12 --version >nul 2>nul && set PY=py -3.12
if not defined PY py -3.11 --version >nul 2>nul && set PY=py -3.11
if not defined PY py -3 --version >nul 2>nul && set PY=py -3
if not defined PY python --version >nul 2>nul && set PY=python
if not defined PY (
  echo  No encuentro Python / Python not found. Instala / install Python 3.12 from python.org
  echo  ^(marca / tick "Add python.exe to PATH"^)
  start https://www.python.org/downloads/release/python-3129/
  pause
  exit /b
)
%PY% -m venv .venv || (echo No se pudo crear el entorno & pause & exit /b)
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt || (echo Fallo instalando dependencias & pause & exit /b)
".venv\Scripts\python.exe" -m pip install -q --no-deps pyrnnoise==0.4.5
timeout /t 2 >nul

:run
".venv\Scripts\python.exe" -c "import PySide6.QtWebEngineWidgets, sounddevice, miniaudio, send2trash" >nul 2>nul || (
  echo  Instalando piezas que faltan / installing missing parts...
  ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
)
".venv\Scripts\python.exe" -c "import importlib.util,sys;sys.exit(0 if importlib.util.find_spec('pyrnnoise') else 1)" >nul 2>nul || ".venv\Scripts\python.exe" -m pip install -q --no-deps pyrnnoise==0.4.5
start "" ".venv\Scripts\pythonw.exe" bubblepad.py
