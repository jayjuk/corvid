docker network inspect orchestrator-network >nul 2>&1 || docker network create orchestrator-network
docker rm orchestrator_do
docker run --network orchestrator-network --env-file .env --name orchestrator_do -p 3001:3001 jayjuk/orchestrator
