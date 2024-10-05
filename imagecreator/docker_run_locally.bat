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
echo Running Image Creator

REM Create a Docker network if it doesn't exist
docker network inspect gameserver-network >nul 2>&1 || docker network create gameserver-network
set "GAMESERVER_HOSTNAME=gameserver_local"
docker rm imagecreator_local
docker run --network gameserver-network --name imagecreator_local ^
           -e GAMESERVER_HOSTNAME=%GAMESERVER_HOSTNAME% ^
           -e GAMESERVER_PORT=%GAMESERVER_PORT% ^
           -e AZURE_STORAGE_ACCOUNT_NAME=%AZURE_STORAGE_ACCOUNT_NAME% ^
           -e AZURE_STORAGE_ACCOUNT_KEY=%AZURE_STORAGE_ACCOUNT_KEY% ^
           -e IMAGE_MODEL_NAME=%IMAGE_MODEL_NAME% ^
           -e MODEL_SYSTEM_MESSAGE=%MODEL_SYSTEM_MESSAGE% ^
           -e OPENAI_API_KEY=%OPENAI_API_KEY% ^
           -e STABILITY_KEY=%STABILITY_KEY% ^
           -e GOOGLE_GEMINI_KEY=%GOOGLE_GEMINI_KEY% ^
           -e GOOGLE_GEMINI_SAFETY_OVERRIDE=%GOOGLE_GEMINI_SAFETY_OVERRIDE% ^
           -e GOOGLE_GEMINI_PROJECT_ID=%GOOGLE_GEMINI_PROJECT_ID% ^
           -e GOOGLE_GEMINI_LOCATION=%GOOGLE_GEMINI_LOCATION% ^
           imagecreator:latest
