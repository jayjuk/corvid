@echo off
call ..\common\load_dotenv.bat
echo Running Image Server...
python imageserver.py
