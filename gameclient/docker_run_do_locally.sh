docker network inspect gameserver-network >nul 2>&1 || docker network create gameserver-network
docker rm gameclient_do
docker run --network gameserver-network --env-file .env --name gameclient_do -p 3000:3000 jayjuk/gameclient
