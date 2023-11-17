echo off
rem call conda activate jaysgame
:loop
echo Running Game Server...
python gameserver.py
echo About to restart...
rem pause
goto loop
rem call conda deactivate
