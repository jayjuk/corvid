docker build -t gameserver . -f gameserver/Dockerfile
docker tag gameserver jayjuk/gameserver
docker push jayjuk/gameserver

