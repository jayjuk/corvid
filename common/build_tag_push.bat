@echo off
setlocal

REM Define the directory and image name
set "repo_name=%1%"
set "service_name=%2%"

REM Check service name set
if "%service_name%"=="" (
    echo ERROR: Service name not provided as command line parameter 2. Repo name is parameter 1
    exit /b 1
)

REM Get the current directory name
for %%i in ("%cd%") do set "current_dir=%%~nxi"

REM Check if the current directory is the service directory
if /i "%current_dir%"=="%service_name%" (
    cd ..
)

docker build -t %service_name% . -f %service_name%\Dockerfile
docker tag %service_name% %repo_name%/%service_name%
docker push %repo_name%/%service_name%

endlocal
