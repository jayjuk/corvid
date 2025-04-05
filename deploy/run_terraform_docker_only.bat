@REM @echo off
@REM REM Check if the IP address parameter is provided
@REM if "%1%"=="" (
@REM     echo Usage: destroy_terraform_docker_only.bat <remote_server_ip>
@REM     exit /b 1
@REM )

@REM REM Define the remote server details
@REM set REMOTE_USER=root
@REM set REMOTE_HOST=%1
@REM set PRIVATE_KEY_PATH=C:/Users/me/.ssh/id_rsa

@REM REM Stop and remove all Docker containers on the remote server
@REM ssh -i %PRIVATE_KEY_PATH% %REMOTE_USER%@%REMOTE_HOST% "docker stop $(docker ps -aq) && docker rm $(docker ps -aq)"

run_terraform.bat docker
