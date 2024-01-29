docker build -t aibroker . -f aibroker\Dockerfile
docker tag aibroker jayjuk/aibroker
docker push jayjuk/aibroker
