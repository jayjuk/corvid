set AI_COUNT=1
set AI_MODE=player
@rem gpt-4-turbo-preview   gemini-pro   gpt-3.5-turbo   claude-3-haiku-20240307
set MODEL_NAME=gemini-pro
echo Loading env variables from common .env file in local execution...
for /F "tokens=1* delims==" %%a in (..\common\.env) do ( set "%%a=%%b" )
echo Running AI Broker...
python aibroker.py %*
