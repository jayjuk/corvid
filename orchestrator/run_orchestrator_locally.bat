@echo off
:loop
echo Loading env variables from common .env file in local execution...
for /F "tokens=1* delims==" %%a in (..\common\.env) do ( set "%%a=%%b" )
echo Running Orchestrator... world = %1
@rem %1 contains world name (optional)
@rem Disable animals while testing to avoid noise
set ANIMALS_ACTIVE=False
python orchestrator.py %1

REM Check for restart.tmp file
if exist restart.tmp (
    echo Found restart flag file! Deleting and restarting...
    del restart.tmp
    goto :loop
)
