@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Running Misbaha with a console window so errors are visible...
python -m pip install --disable-pip-version-check -r requirements.txt
python "%~dp0Misbaha.pyw"
echo.
echo (Errors are also saved in %%APPDATA%%\Misbaha\error.log and crash.log)
pause
