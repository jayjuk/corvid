@echo off
call ..\common\load_dotenv.bat
set PYTHONPATH=%PYTHONPATH%
echo Running Image Server...
python imageserver.py
