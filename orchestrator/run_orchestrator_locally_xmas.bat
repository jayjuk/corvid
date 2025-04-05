@echo off
:: Check if common folder is in PYTHONPATH
echo %PYTHONPATH% | findstr /C:"..\common" >nul
if errorlevel 1 (
    echo The common folder is not in PYTHONPATH. Adding it now...
    set PYTHONPATH=..\common;%PYTHONPATH%
):loop
echo Loading env variables from common .env file in local execution...
for /F "tokens=1* delims==" %%a in (..\common\.env) do ( set "%%a=%%b" )
echo Running Orchestrator... world = xmas
python orchestrator.py xmas

REM Check for restart.tmp file
if exist restart.tmp (
    echo Found restart flag file! Deleting and restarting...
    del restart.tmp
    goto :loop
)
