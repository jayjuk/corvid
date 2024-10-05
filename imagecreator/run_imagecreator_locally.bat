@echo off
echo Loading env variables from common .env file in local execution...
for /F "tokens=1* delims==" %%a in (..\common\.env) do ( set "%%a=%%b" )
@rem gpt-4-turbo-preview   gemini-pro   gpt-3.5-turbo   claude-3-haiku-20240307   mixtral-8x7b-32768  llama3-70b-8192  llama3-8b-8192
echo Running Game AI Worker with model %MODEL_NAME%...

python imagecreator.py
