@echo off
echo Loading env variables from common .env file in local execution...
for /F "tokens=1* delims==" %%a in (..\common\.env) do ( set "%%a=%%b" )
@REM Gemini no good at generating image prompts!
set MODEL_NAME=gpt-4o
@REM set IMAGE_MODEL_NAME=gpt-4o
echo Running Image creator with landscape %LANDSCAPE_DESCRIPTION%, text model model %MODEL_NAME% and image model %IMAGE_MODEL_NAME%...
python imagecreator.py
