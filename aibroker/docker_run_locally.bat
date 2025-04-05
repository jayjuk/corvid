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

REM Create a Docker network if it doesn't exist
docker network inspect orchestrator-network >nul 2>&1 || docker network create orchestrator-network

echo Running AI Broker
set "ORCHESTRATOR_HOSTNAME=orchestrator_local"
docker rm aibroker_local
docker run --network orchestrator-network --name aibroker_local ^
           -e AI_COUNT=1 ^
           -e MODEL_NAME=%MODEL_NAME% ^
           -e OPENAI_API_KEY=%OPENAI_API_KEY% ^
           -e STABILITY_KEY=%STABILITY_KEY% ^
           -e ANTHROPIC_API_KEY=%ANTHROPIC_API_KEY% ^
           -e GROQ_API_KEY=%GROQ_API_KEY% ^
           -e GOOGLE_GEMINI_KEY=%GOOGLE_GEMINI_KEY% ^
           -e GOOGLE_GEMINI_PROJECT_ID=%GOOGLE_GEMINI_PROJECT_ID% ^
           -e GOOGLE_GEMINI_LOCATION=%GOOGLE_GEMINI_LOCATION% ^
           -e GOOGLE_GEMINI_SAFETY_OVERRIDE=%GOOGLE_GEMINI_SAFETY_OVERRIDE% ^
           -e ORCHESTRATOR_HOSTNAME=corvid.westeurope.azurecontainer.io ^
           -e ORCHESTRATOR_PORT=3001 ^
           -p 3001:3001 aibroker:latest
