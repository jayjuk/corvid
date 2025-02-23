@echo off
echo Loading env variables from common .env file in local execution...
for /F "tokens=1* delims==" %%a in (..\common\.env) do ( set "%%a=%%b" )
@rem set MODEL_NAME=gpt-4o-mini
echo Running AI Requester with model %MODEL_NAME%...
set MODEL_SYSTEM_MESSAGE=
set MODEL_DEBUG_MODE=False
python airequester.py
