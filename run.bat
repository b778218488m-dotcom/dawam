@echo off
setlocal
set PY=
py -3 --version >nul 2>nul && set PY=py -3
if "%PY%"=="" python --version >nul 2>nul && set PY=python
if "%PY%"=="" goto nopy
%PY% -m pip install -r requirements.txt
%PY% dawam.py
pause
exit /b 0
:nopy
echo Python was not found. Install it from python.org and tick "Add Python to PATH".
pause
