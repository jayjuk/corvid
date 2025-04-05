@echo off
:: Check if common folder is in PYTHONPATH
echo %PYTHONPATH% | findstr /C:"..\common" >nul
if errorlevel 1 (
    echo The common folder is not in PYTHONPATH. Adding it now...
    set PYTHONPATH=..\common;%PYTHONPATH%
)
echo Loading env variables from common .env file in local execution...
for /F "tokens=1* delims==" %%a in (..\common\.env) do ( set "%%a=%%b" )
echo Running Orchestrator...
@rem Disable animals while testing to avoid noise
set ANIMALS_ACTIVE=False
python orchestrator.py blankworld
