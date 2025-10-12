@echo off
echo Loading env variables from common .env file in local execution...
for /F "tokens=1* delims==" %%a in (..\common\.env) do ( set "%%a=%%b" )
rem Gemini models do not seem to handle custom requests well
rem #gpt-4o-mini
rem set AIREQUESTER_MODEL_NAME=gpt-5-nano
echo Running AI Requester...
if defined AIREQUESTER_MODEL_NAME (
    echo Using model: %AIREQUESTER_MODEL_NAME%
) else if defined MODEL_NAME (
    echo Using model: %MODEL_NAME%
) else (
    echo Using default model
)
set MODEL_SYSTEM_MESSAGE=
set MODEL_DEBUG_MODE=False
python airequester.py
