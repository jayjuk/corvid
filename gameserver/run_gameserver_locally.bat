@echo off
rem :loop
echo Loading env variables from common .env file in local execution...
for /F "tokens=1* delims==" %%a in (..\common\.env) do ( set "%%a=%%b" )
echo Running Game Server... mode = %1
python gameserver.py %1
rem echo About to restart...
rem pause
rem goto loop
rem call conda deactivate
