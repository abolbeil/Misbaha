@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem Builds dist\Misbaha.exe  (single portable file).  Use "build_exe.bat onedir" for a folder build
rem (starts faster and is less often flagged by antivirus software).
set "MODE=--onefile"
if /i "%~1"=="onedir" set "MODE=--onedir"

rem Hash-locked: pip refuses any package whose contents differ from the reviewed versions.
python -m pip install --disable-pip-version-check --require-hashes -r requirements-build.lock
if errorlevel 1 ( echo pip failed & pause & exit /b 1 )
python scripts\write_build_info.py
python -m PyInstaller --noconfirm --clean %MODE% --noconsole --name Misbaha ^
  --icon assets\misbaha.ico ^
  --version-file scripts\version_info.txt ^
  --add-data "misbaha\fonts;misbaha\fonts" ^
  --exclude-module tkinter ^
  Misbaha.pyw
if errorlevel 1 ( echo Build failed & pause & exit /b 1 )
echo.
echo Done. Your app is in the dist folder.
if /i not "%CI%"=="true" pause
