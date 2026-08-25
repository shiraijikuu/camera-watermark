@echo off
chcp 65001 >nul
cd /d "%~dp0"
start "" "%~dp0..\python\pythonw.exe" "%~dp0app.py"
