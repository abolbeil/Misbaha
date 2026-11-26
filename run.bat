@echo off
chcp 65001 >nul
cd /d "%~dp0"

python --version >nul 2>nul
if errorlevel 1 goto nopython

rem --- skip installing if everything is already there ---
python -c "import PySide6.QtWidgets, PySide6.QtNetwork" >nul 2>nul
if not errorlevel 1 goto launch

echo First run: downloading PySide6 [about 80 MB]. This can take a few minutes.
echo.
python -m pip install --disable-pip-version-check --timeout 60 --retries 3 -r requirements.txt
if errorlevel 1 goto pipfail

:launch
for /f "delims=" %%i in ('python -c "import sys,os;p=os.path.join(os.path.dirname(sys.executable),'pythonw.exe');print(p if os.path.exists(p) else sys.executable)"') do set "PYW=%%i"
start "" "%PYW%" "%~dp0Misbaha.pyw"
echo Misbaha started - look at the bottom-right of your screen.
timeout /t 3 >nul
exit /b 0

:nopython
echo Python is not installed or not on PATH.
echo Install it from https://www.python.org/downloads/  and tick "Add python.exe to PATH".
pause
exit /b 1

:pipfail
echo.
echo Could not download the requirements.
echo - Check your internet connection.
echo - On a company network with a proxy, run:
echo     python -m pip install --proxy http://YOUR-PROXY:PORT -r requirements.txt
echo   then run run.bat again.
pause
exit /b 1
