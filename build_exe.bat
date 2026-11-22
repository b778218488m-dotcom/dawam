@echo off
setlocal
set PY=
py -3 --version >nul 2>nul && set PY=py -3
if "%PY%"=="" python --version >nul 2>nul && set PY=python
if "%PY%"=="" goto nopy
echo Using: %PY%
%PY% -m pip install --upgrade pip
%PY% -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto fail
%PY% -m PyInstaller --noconfirm --clean --onefile --windowed --name Fekra-Dawam dawam.py
if errorlevel 1 goto fail
echo.
echo DONE. Your program is here: dist\Fekra-Dawam.exe
pause
exit /b 0
:nopy
echo Python was not found.
echo Install it from python.org and tick "Add Python to PATH", then run this file again.
pause
exit /b 1
:fail
echo Something went wrong. Take a screenshot of the messages above.
pause
exit /b 1
