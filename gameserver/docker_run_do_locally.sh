docker network inspect gameserver-network >nul 2>&1 || docker network create gameserver-network
docker rm gameserver_do
docker run --network gameserver-network --env-file .env --name gameserver_do -p 3001:3001 jayjuk/gameserver
