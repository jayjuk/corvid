docker build -t orchestrator . -f orchestrator/Dockerfile
docker tag orchestrator jayjuk/orchestrator
docker push jayjuk/orchestrator

