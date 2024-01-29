docker build -t gameclient . -f gameclient\Dockerfile
docker tag gameclient jayjuk/gameclient
docker push jayjuk/gameclient
