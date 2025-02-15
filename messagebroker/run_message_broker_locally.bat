@echo off
REM Run RabbitMQ
docker rm -f rabbitmq
docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:management
echo Sleeping for 3 seconds...
timeout /t 3 /nobreak >nul
echo Started RabbitMQ in container
echo Loading env variables from common .env file in local execution...
for /F "tokens=1* delims==" %%a in (..\common\.env) do ( set "%%a=%%b" )
echo Running Message Broker:
python message_broker.py
