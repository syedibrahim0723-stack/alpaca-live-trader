@echo off
title News Radar installer
setlocal

:: Where the local copy goes. Change this line to install somewhere else.
set "TARGET=%USERPROFILE%\NewsRadar"

set "BRANCH=claude/eager-goldberg-fxx9vl"
set "ZIPURL=https://github.com/syedibrahim0723-stack/alpaca-live-trader/archive/refs/heads/%BRANCH%.zip"
set "TMPDIR=%TEMP%\news_radar_install"

echo News Radar installer
echo --------------------
echo Installing to: %TARGET%
echo.

if exist "%TMPDIR%" rmdir /s /q "%TMPDIR%"
mkdir "%TMPDIR%"

echo Downloading the app from GitHub...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%ZIPURL%' -OutFile '%TMPDIR%\app.zip'; Expand-Archive -Path '%TMPDIR%\app.zip' -DestinationPath '%TMPDIR%' -Force"
if errorlevel 1 (
    echo Download failed. Check your internet connection and try again.
    pause
    exit /b 1
)

set "SRC="
for /d %%D in ("%TMPDIR%\alpaca-live-trader-*") do set "SRC=%%D\news_radar"
if not defined SRC (
    echo Could not find the news_radar folder in the download.
    pause
    exit /b 1
)

echo Copying files...
:: Keeps your existing keys (.env), database (data) and virtualenv when updating.
robocopy "%SRC%" "%TARGET%" /E /NFL /NDL /NJH /NJS /NP /XD data .venv /XF .env >nul
if errorlevel 8 (
    echo Copy failed.
    pause
    exit /b 1
)
rmdir /s /q "%TMPDIR%"

echo Creating desktop shortcut...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\News Radar.lnk'); $s.TargetPath='%TARGET%\run.bat'; $s.WorkingDirectory='%TARGET%'; $s.Save()" >nul 2>nul

echo.
echo Installed. Use the "News Radar" shortcut on your desktop, or run:
echo   %TARGET%\run.bat
echo Run this installer again any time to update (your keys and data are kept).
echo.
echo Starting the app now...
call "%TARGET%\run.bat"
