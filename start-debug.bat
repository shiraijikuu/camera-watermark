@echo off
chcp 65001 >nul
cd /d "%~dp0"
where python >nul 2>nul
if %errorlevel%==0 (
  python app.py
  pause
  exit /b
)
where py >nul 2>nul
if %errorlevel%==0 (
  py app.py
  pause
  exit /b
)
echo *~0 Python÷H‰Å Python 3.10+þ	 Add to PATH	
pause
