@echo off
REM Check for .env file in ..\common
if exist "..\common\.env" (
    set "env_file_path=..\common\.env"
) else (
    REM Check for .env file in .\common
    if exist ".\common\.env" (
        set "env_file_path=.\common\.env"
    ) else (
        echo .env file not found in ..\common or .\common.
        exit /b 1
    )
)
echo Running Image Server...
set "GAMESERVER_HOSTNAME=gameserver_local"
docker rm gameclient_local
docker run --name gameclient_local -p 3000:3000 jayjuk/gameclient
