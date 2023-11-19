echo off
rem call conda activate jaysgame
:loop
echo Running Game Server... mode = %1
python gameserver.py %1
echo About to restart...
rem pause
goto loop
rem call conda deactivate
