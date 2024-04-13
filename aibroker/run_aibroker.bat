set AI_COUNT=1
set AI_MODE=player
echo Loading env variables from common .env file in local execution...
for /F "tokens=1* delims==" %%a in (..\common\.env) do ( set "%%a=%%b" )
@rem gpt-4-turbo-preview   gemini-pro   gpt-3.5-turbo   claude-3-haiku-20240307
set MODEL_NAME=claude-3-haiku-20240307
echo Running AI Broker with model %MODEL_NAME%...
python aibroker.py %*
