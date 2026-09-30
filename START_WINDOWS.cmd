@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe py -m venv .venv
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m playwright install chromium
if errorlevel 1 goto failed
.venv\Scripts\python.exe pdf_generator.py
if errorlevel 1 goto failed
pause
exit /b 0
:failed
 echo Installation or generation failed. Send the terminal output for diagnosis.
 pause
 exit /b 1
