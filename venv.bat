@echo off
if not exist logs mkdir logs
if not exist py3 virtualenv -p 3 .\py3 > .\logs\venv.log 2>&1
call .\py3\scripts\activate.bat >> .\logs\venv.log 2>&1
@echo Python virtual environment successfully configured. Run 'deactivate' to restore environment.