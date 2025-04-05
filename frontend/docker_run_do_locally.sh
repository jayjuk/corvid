docker network inspect gameserver-network >nul 2>&1 || docker network create gameserver-network
docker rm frontend_do
docker run --network gameserver-network --env-file .env --name frontend_do -p 3000:3000 jayjuk/frontend
