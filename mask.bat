@echo off
rem Mask for Windows.
rem   Double-click: opens Mask in your browser.
rem   In PowerShell in this folder:  ./mask help
setlocal
chcp 65001 >nul
set "KIT=%~dp0"
set "PY=%KIT%envs\mask\Scripts\python.exe"
if exist "%PY%" goto run
echo Mask isn't installed yet. Double-click install-windows.bat first.
if "%~1"=="" pause
exit /b 1
:run
set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONUTF8=1"
"%PY%" "%KIT%app\mask.py" %*
set "CODE=%ERRORLEVEL%"
if "%~1"=="" pause
exit /b %CODE%
