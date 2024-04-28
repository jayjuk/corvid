@echo off
tasklist /FI "IMAGENAME eq Docker Desktop.exe" 2>NUL | find /I /N "Docker Desktop.exe">NUL
if "%ERRORLEVEL%"=="1" (
    echo Launching Docker Desktop...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    echo Waiting for Docker Desktop to start...
    timeout /T 10
)
echo Running unit tests as per GHA using Act
echo Game Server:
"C:\Act\Act.exe" -j test_imageserver
echo AI Broker:
"C:\Act\Act.exe" -j test_aibroker
echo Image Server:
"C:\Act\Act.exe" -j test_imageserver

