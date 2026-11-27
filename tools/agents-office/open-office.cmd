@echo off
rem Agents Office launcher (Windows): double-click. Starts the viewer for this project and opens the browser.
cd /d "%~dp0..\.."
where node >nul 2>nul
if errorlevel 1 (
  echo Agents Office needs Node.js 18 or newer: https://nodejs.org
  start "" https://nodejs.org
  pause
  exit /b 1
)
node "tools\agents-office\office.mjs" start --open --project "%CD%"
if errorlevel 1 pause
