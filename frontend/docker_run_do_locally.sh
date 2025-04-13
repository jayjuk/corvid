docker network inspect orchestrator-network >nul 2>&1 || docker network create orchestrator-network
docker rm frontend_do
docker run --network orchestrator-network --env-file .env --name frontend_do -p 3000:3000 jayjuk/frontend
