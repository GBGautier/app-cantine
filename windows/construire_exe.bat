@echo off
chcp 65001 >nul
cd /d "%~dp0.."
rem (ce script est dans windows\ : on travaille depuis le dossier du projet, ou se trouvent venv\ et les donnees)
title Construction de CGRS.exe

rem Construit dist\CGRS.exe (un seul fichier, à copier sur n'importe quel poste Windows : Python n'est pas nécessaire).
if not exist "venv\Scripts\python.exe" (
  py -3.13 -m venv venv 2>nul || py -3.12 -m venv venv 2>nul || python -m venv venv
)
"venv\Scripts\python.exe" -m pip install -r requirements.txt -r requirements\build.txt
if errorlevel 1 ( echo Installation des dependances impossible. & pause & exit /b 1 )
"venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean windows\cgrs.spec
if errorlevel 1 ( echo La construction a echoue. & pause & exit /b 1 )
echo.
echo Termine : dist\CGRS.exe
echo Les donnees (base, PDF, sauvegardes, journal) seront dans %%LOCALAPPDATA%%\CGRS
pause
