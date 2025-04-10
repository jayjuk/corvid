@echo off
echo Loading env variables from common .env file in local execution...

REM Check for .env file in ..\common
if exist "..\common\.env" (
    set "env_file_path=..\common\.env"
) else (
    REM Check for .env file in .\common
    if exist ".\common\.env" (
        set "env_file_path=.\common\.env"
    ) else (
        echo .env file not found in ..\common or .\common.
        exit /b 1
    )
)

REM Load the environment variables from the .env file
for /F "tokens=1* delims==" %%a in (%env_file_path%) do (
    set "%%a=%%b"
)
