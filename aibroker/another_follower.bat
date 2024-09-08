@echo off
set AI_COUNT=1

echo Loading env variables from common .env file in local execution...
for /F "tokens=1* delims==" %%a in (..\common\.env) do ( set "%%a=%%b" )

set MODEL_NAME=gpt-4o-mini
set AI_MODE=builder
set AI_NAME=Caesar
set MODEL_SYSTEM_MESSAGE="%AI_NAME% is your leader and big boss, check with him before you build, and after each world, he MUST approve before you do another one, so you can learn."
set AI_NAME=%1%
python aibroker.py
