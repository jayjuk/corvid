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
REM Load the environment variables from the .env file
echo Loading env variables from common .env file in local execution...
for /F "tokens=1* delims==" %%a in (%env_file_path%) do (
    set "%%a=%%b"
)

REM Run the docker container
echo Running Image Server
set "ORCHESTRATOR_HOSTNAME=orchestrator_local"
docker rm imageserver_local
docker run --network orchestrator-network --name imageserver_local ^
           -e IMAGESERVER_HOSTNAME=%IMAGESERVER_HOSTNAME% ^
           -e IMAGESERVER_PORT=%IMAGESERVER_PORT% ^
           -e AZURE_STORAGE_ACCOUNT_NAME=%AZURE_STORAGE_ACCOUNT_NAME% ^
           -e AZURE_STORAGE_ACCOUNT_KEY=%AZURE_STORAGE_ACCOUNT_KEY% ^
           -p 3002:3002 ^
           imageserver:latest
