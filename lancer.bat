@echo off
chcp 65001 >nul
cd /d "%~dp0"
title CGRS

rem --- 1. environnement Python (cree une seule fois) ---
if not exist "venv\Scripts\python.exe" (
  echo Creation de l environnement Python...
  py -3.13 -m venv venv 2>nul || py -3.12 -m venv venv 2>nul || python -m venv venv
  if errorlevel 1 (
    echo.
    echo Impossible de creer l environnement. Python 3.12 ou 3.13 est-il installe ?
    pause
    exit /b 1
  )
)

rem --- 2. dependances (installees seulement si requirements.txt a change) ---
fc /b requirements.txt "venv\requirements.installe" >nul 2>nul
if errorlevel 1 (
  echo Installation des dependances...
  "venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo.
    echo L installation a echoue. Copiez le message ci-dessus.
    pause
    exit /b 1
  )
  copy /y requirements.txt "venv\requirements.installe" >nul
)

rem --- 3. lancement ---
echo.
echo CGRS demarre sur http://localhost:8000  (fermez cette fenetre pour arreter)
start "" /b cmd /c "timeout /t 3 >nul & start http://localhost:8000"
"venv\Scripts\python.exe" -m uvicorn app:app --port 8000
pause
