@echo off
echo Loading env variables from common .env file in local execution...
for /F "tokens=1* delims==" %%a in (..\common\.env) do ( set "%%a=%%b" )
echo Running Game Server...
@rem Disable animals while testing to avoid noise
set ANIMALS_ACTIVE=False
python gameserver.py blankworld

