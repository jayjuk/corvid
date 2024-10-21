echo Running team of AI players

@echo off
set AI_COUNT=1

echo Loading env variables from common .env file in local execution...
for /F "tokens=1* delims==" %%a in (..\common\.env) do ( set "%%a=%%b" )

@rem Create leader by calling run_aibroker_locally.bat with the model name and system message
rem set MODEL_NAME=gpt-4o
set AI_LEADER_NAME=Caesar
set AI_NAME=%AI_LEADER_NAME%
set AI_MODE=player
set WORLD_BRIEFING=You are part of a team of players who are building a new game world. You can build locations, create items and spawn creatures.^
 The theme is UNDERWATER. Use your imagination and draw from all fictional sources (whether book or film) you like. Try to be consistent and logical, for example from one location to the next.
set MODEL_SYSTEM_MESSAGE=%WORLD_BRIEFING% You are the leader. It is your responsibility to oversee the construction of a really interesting and entertaining new world, with the help of your team.^
 Use leadership and management skills above all. Supervise closely and above all, communicate.
start cmd /k "python aibroker.py"

@rem Create followers 
@rem llama3-70b-8192
rem set MODEL_NAME=gpt-4o
set AI_MODE=builder
set AI_NAME=Brutus
set MODEL_SYSTEM_MESSAGE=%WORLD_BRIEFING% Follow %AI_LEADER_NAME% above all, do not stray from the path of %AI_LEADER_NAME%'s vision, do everything you can to help %AI_LEADER_NAME% succeed.^
 Ask %AI_LEADER_NAME% for input before building, and then ask him again to check your work and provide feedback on a regular basis.
timeout /t 3
start cmd /k "python aibroker.py"

timeout /t 3
rem set MODEL_NAME=gpt-4o-mini
set AI_NAME=Cassandra
set AI_MODE=builder
set MODEL_SYSTEM_MESSAGE=%WORLD_BRIEFING% %AI_LEADER_NAME% is your leader and big boss, talk to him about what he wants before you build, and after each world, he MUST approve before you do another one, so you can learn.
set AI_NAME=%1%
python aibroker.py

