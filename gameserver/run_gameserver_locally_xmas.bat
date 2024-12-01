@echo off
:loop
echo Loading env variables from common .env file in local execution...
for /F "tokens=1* delims==" %%a in (..\common\.env) do ( set "%%a=%%b" )
echo Running Game Server... world = xmas
python gameserver.py xmas

REM Check for restart.tmp file
if exist restart.tmp (
    echo Found restart flag file! Deleting and restarting...
    del restart.tmp
    goto :loop
)
