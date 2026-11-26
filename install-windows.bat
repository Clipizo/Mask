@echo off
rem Mask installer for Windows. Double-click this file.
rem It gets "uv" (a small tool that installs Python) and Python into this folder,
rem then runs app\setup_kit.py, which does the rest. Everything goes into this
rem folder (only Microsoft's Visual C++ component, if Windows lacks it, is
rem installed on the computer, after asking).
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title Mask installer

set "NOPAUSE="
for %%A in (%*) do if /i "%%~A"=="--yes" set "NOPAUSE=1"

set "KIT=%~dp0"
rem Ignore Python settings that other programs may have left on this computer.
set "PYTHONHOME="
set "PYTHONPATH="
rem The uv version this kit was tested with, and the SHA-256 of its Windows download
rem (uv-x86_64-pc-windows-msvc.zip, as published by uv).
set "UV_VERSION=0.13.7"
set "UV_SHA256=0cdc5b38fe5a8168ed6a25814f5ba43c21d313dd3187314fccb37b7cec46e021"
set "UV_DIR=%KIT%.tools\uv"
rem uv keeps Python and its downloads in this folder too.
set "UV_PYTHON_INSTALL_DIR=%KIT%.tools\python"
set "UV_CACHE_DIR=%KIT%.tools\uv-cache"
set "UV_PYTHON_PREFERENCE=only-managed"
set "UV_NO_CONFIG=1"
set "UV_HTTP_TIMEOUT=300"
set "UV_HTTP_CONNECT_TIMEOUT=60"
set "UV_HTTP_RETRIES=8"

rem Get uv and Python (app\bootstrap.ps1). While it works, a click inside this window
rem doesn't pause it; app\setup_kit.py then does the same for the rest of the install.
powershell -NoProfile -ExecutionPolicy Bypass -File "%KIT%app\bootstrap.ps1" -UvDir "%UV_DIR%" -UvVersion %UV_VERSION% -UvSha256 %UV_SHA256%
set "UV=%UV_DIR%\uv.exe"
if exist "%UV%" goto have_uv
if exist "%UV_DIR%\bin\uv.exe" set "UV=%UV_DIR%\bin\uv.exe"
if exist "%UV%" goto have_uv

rem If that script couldn't run (some company PCs block script files), get uv the usual way.
echo Downloading uv (a small tool that installs Python for Mask)...
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor 3072; $env:UV_UNMANAGED_INSTALL='%UV_DIR%'; irm https://astral.sh/uv/%UV_VERSION%/install.ps1 | iex"
if exist "%UV_DIR%\uv.exe" set "UV=%UV_DIR%\uv.exe"
if exist "%UV_DIR%\bin\uv.exe" set "UV=%UV_DIR%\bin\uv.exe"
if exist "%UV%" goto have_uv

rem Fall back to a uv that is already installed on this computer.
for /f "delims=" %%U in ('where uv 2^>nul') do set "UV=%%U"
if exist "%UV%" goto have_uv

echo.
echo Could not download uv. Check your internet connection and try again.
echo If it still fails, your network may block astral.sh or github.com.
if not defined NOPAUSE pause
exit /b 1

:have_uv
set "KIT_UV=%UV%"
"%UV%" run --no-project --python 3.12 "%KIT%app\setup_kit.py" %*
set "CODE=%ERRORLEVEL%"
echo.
if "%CODE%"=="2" echo If the text above is about a download, check your internet connection and run the installer again.
if not defined NOPAUSE pause
exit /b %CODE%
