@echo off
echo Loading env variables from common .env file in local execution...
for /F "tokens=1* delims==" %%a in (..\common\.env) do ( set "%%a=%%b" )
echo Running AI Person Manager with model %MODEL_NAME%...
if "%~1"=="" (
    set AI_AGENT_FILE_NAME=ai_agents.json
) else (
    set AI_AGENT_FILE_NAME=%~1
)
set AIBROKER_MAX_HISTORY=100
set MODEL_SYSTEM_MESSAGE=You are a character in a simulated world.
python agentmanager.py
