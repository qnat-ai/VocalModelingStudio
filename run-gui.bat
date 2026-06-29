@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv" (
    echo Blad: Nie znaleziono srodowiska wirtualnego .venv.
    echo Uruchom najpierw instalacje zaleznosci.
    pause
    exit /b 1
)
echo Uruchamianie Vocal Modeling Studio GUI...
".venv\Scripts\python.exe" main.py --gui
pause
