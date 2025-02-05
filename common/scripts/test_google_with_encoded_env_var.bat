@echo off
echo Loading env variables from common .env file in local execution...
for /F "tokens=1* delims==" %%a in (..\.env) do ( set "%%a=%%b" )
python test_google_with_encoded_env_var.py
