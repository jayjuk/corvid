echo Running team of AI players

@echo off
set AI_COUNT=1

echo Loading env variables from common .env file in local execution...
for /F "tokens=1* delims==" %%a in (..\common\.env) do ( set "%%a=%%b" )

@rem Create leader by calling run_aibroker_locally.bat with the model name and system message
set MODEL_NAME=gpt-4o-mini
set AI_NAME=Caesar
set AI_MODE=player
set MODEL_SYSTEM_MESSAGE="You are the leader. It is your responsibility to oversee the construction of a really interesting and entertaining new world, with the help of your team. Use leadership and management skills above all. Supervise closely and above all, communicate."
start cmd /k "python aibroker.py"

@rem Create followers 
@rem llama3-70b-8192
set MODEL_NAME=gpt-4o-mini
set AI_MODE=builder
set MODEL_SYSTEM_MESSAGE="Follow %AI_NAME% above all, do not stray from the path of %AI_NAME%'s vision, do everything you can to help %AI_NAME% succeed. Invite %AI_NAME% to check your work and provide feedback on a regular basis."
set AI_NAME=Brutus
timeout /t 3
python aibroker.py
