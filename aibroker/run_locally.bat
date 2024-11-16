@echo off
echo Loading env variables from common .env file in local execution...
for /F "tokens=1* delims==" %%a in (..\common\.env) do ( set "%%a=%%b" )
echo Running AI Requester with model %MODEL_NAME%...
if "%~1"=="" (
    set AI_PLAYER_FILE_NAME=no_ai_players.json
) else (
    set AI_PLAYER_FILE_NAME=%~1
)
python playermanager.py
