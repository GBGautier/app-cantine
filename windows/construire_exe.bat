@echo off
chcp 65001 >nul
cd /d "%~dp0.."
rem (ce script est dans windows\ : on travaille depuis le dossier du projet, ou se trouvent venv\ et les donnees)
title Construction de Cantine.exe

rem Usage : construire_exe.bat         -> dist\Cantine.exe
rem          construire_exe.bat debug   -> dist\Cantine-debug.exe (avec une console qui affiche les erreurs de demarrage)
rem Construit dist\Cantine.exe (un seul fichier, à copier sur n'importe quel poste Windows : Python n'est pas nécessaire).
if /i "%~1"=="debug" set CGRS_DEBUG=1
rem un Cantine.exe (ou un ancien CGRS.exe) encore ouvert (ou bloque en arriere-plan) empeche de remplacer le fichier : on le ferme
taskkill /f /im Cantine.exe >nul 2>&1
taskkill /f /im Cantine-debug.exe >nul 2>&1
taskkill /f /im CGRS.exe >nul 2>&1
taskkill /f /im CGRS-debug.exe >nul 2>&1
if not exist "venv\Scripts\python.exe" (
  py -3.13 -m venv venv 2>nul || py -3.12 -m venv venv 2>nul || python -m venv venv
)
"venv\Scripts\python.exe" -m pip install -r requirements.txt -r requirements\build.txt
if errorlevel 1 ( echo Installation des dependances impossible. & pause & exit /b 1 )
"venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean windows\cgrs.spec
if errorlevel 1 ( echo La construction a echoue. & pause & exit /b 1 )
echo.
if "%CGRS_DEBUG%"=="1" ( echo Termine : dist\Cantine-debug.exe ) else ( echo Termine : dist\Cantine.exe )
echo Les donnees (base, PDF, sauvegardes, journal) seront dans %%LOCALAPPDATA%%\Cantine
pause
