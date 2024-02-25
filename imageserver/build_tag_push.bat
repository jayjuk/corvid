docker build -t imageserver . -f imageserver\Dockerfile
docker tag imageserver jayjuk/imageserver
docker push jayjuk/imageserver
