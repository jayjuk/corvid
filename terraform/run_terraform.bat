@echo off
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
echo Loading env variables from common .env file in local execution...
for /F "tokens=1* delims==" %%a in (%env_file_path%) do (
    set "TF_VAR_%%a=%%b"
)

REM Check if the first parameter is "docker" (case insensitive)
if /I "%1" NEQ "docker" (
    cd droplet_configuration
    terraform plan -out=infra.out
    terraform apply "infra.out"
    cd ..
)

REM Set some variables
set "TF_VAR_AI_COUNT=1"
set TF_VAR_MODEL_SYSTEM_MESSAGE=""

REM Execute Terraform
cd docker_configuration
terraform plan -out=infra.out
terraform apply "infra.out"
cd ..
echo Terraform execution completed.
endlocal
