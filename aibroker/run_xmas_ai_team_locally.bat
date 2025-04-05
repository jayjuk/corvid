echo Running team of AI players

@echo off
set AI_COUNT=1

echo Loading env variables from common .env file in local execution...
for /F "tokens=1* delims==" %%a in (..\common\.env) do ( set "%%a=%%b" )

set WORLD_BRIEFING=You are part of a team of players who are building a new world. You can build locations, create items and spawn creatures.^
 The theme is CHRISTMAS. The setting is %LANDSCAPE_DESCRIPTION%. Be sure to create a vibrant and fun world.^
 Use your imagination and draw from all fictional sources (whether book or film) you like. Try to be consistent and logical, for example from one location to the next, ensure the layout of the world makes sense.

@rem Create leader by calling run_aibroker_locally.bat with the model name and system message
rem set MODEL_NAME=gpt-4o
@REM set AI_LEADER_NAME=Caesar
@REM set AI_NAME=%AI_LEADER_NAME%
@REM set AI_MODE=player

@REM set MODEL_SYSTEM_MESSAGE=%WORLD_BRIEFING% You are the leader. It is your responsibility to oversee the construction of a really interesting and entertaining new world, with the help of your team.^
@REM  Use leadership and management skills above all. Supervise closely and above all, communicate.
@REM start "%AI_NAME%" cmd /k "python aibroker.py"

@rem Create followers 
@rem llama3-70b-8192
rem set MODEL_NAME=gpt-4o
set AI_MODE=builder
set AI_NAME=Bob
set MODEL_SYSTEM_MESSAGE=%WORLD_BRIEFING%
timeout /t 3
start "%AI_NAME%" cmd /k "python aibroker.py"

set AI_MODE=builder
set AI_NAME=Alice
set MODEL_SYSTEM_MESSAGE=%WORLD_BRIEFING%
timeout /t 3
start "%AI_NAME%" cmd /k "python aibroker.py"


@REM timeout /t 3
@REM rem set MODEL_NAME=gpt-4o-mini
@REM set AI_NAME=Cassie
@REM set AI_MODE=builder
@REM set MODEL_SYSTEM_MESSAGE=%WORLD_BRIEFING% %AI_LEADER_NAME% is your leader and big boss, talk to him about what he wants before you build, and after each world, he MUST approve before you do another one, so you can learn.
@REM set AI_NAME=%1%
@REM start "%AI_NAME%" cmd /k "python aibroker.py"

@REM timeout /t 3
@REM rem set MODEL_NAME=gpt-4o-mini
@REM set AI_NAME=Alex
@REM set AI_MODE=builder
@REM set MODEL_SYSTEM_MESSAGE=%WORLD_BRIEFING% %AI_LEADER_NAME% is your leader and big boss, talk to him about what he wants before you build, and after each world, he MUST approve before you do another one, so you can learn.
@REM set AI_NAME=%1%
@REM start "%AI_NAME%" cmd /k "python aibroker.py"

echo All done - launched AI players

