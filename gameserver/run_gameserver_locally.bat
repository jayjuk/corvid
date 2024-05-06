@echo off
:loop
echo Loading env variables from common .env file in local execution...
for /F "tokens=1* delims==" %%a in (..\common\.env) do ( set "%%a=%%b" )
echo Running Game Server... mode = %1
if not "%1"=="" (
    set "MODEL_NAME=%1"
)
python gameserver.py %2

REM Check for restart.tmp file
if exist restart.tmp (
    echo Found restart flag file! Deleting and restarting...
    del restart.tmp
    goto :loop
)

rem echo About to restart...
rem pause
rem goto loop
rem call conda deactivate
