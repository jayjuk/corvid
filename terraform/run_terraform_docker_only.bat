@echo off
REM Check if the IP address parameter is provided
if "%1%"=="" (
    echo Usage: destroy_terraform_docker_only.bat <remote_server_ip>
    exit /b 1
)

REM Define the remote server details
set REMOTE_USER=root
set REMOTE_HOST=%1
set PRIVATE_KEY_PATH=C:/Users/me/.ssh/id_rsa

REM Stop and remove all Docker containers on the remote server
ssh -i %PRIVATE_KEY_PATH% %REMOTE_USER%@%REMOTE_HOST% "docker stop $(docker ps -aq) && docker rm $(docker ps -aq)"

run_terraform.bat docker
