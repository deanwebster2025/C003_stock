@echo off
cd /d "%~dp0"
py server.py --open
if errorlevel 1 pause
