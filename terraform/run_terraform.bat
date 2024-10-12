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
cd droplet_configuration
terraform plan -out=infra.out
terraform apply "infra.out"
cd ..
cd docker_configuration
terraform plan -out=infra.out
terraform apply "infra.out"
cd ..
echo Terraform execution completed.
