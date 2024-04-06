echo "Loading env variables from common .env file in local execution..."
while IFS='=' read -r key value
do
  export "$key=$value"
done < "../common/.env"
echo Running Game Server...
python gameserver.py
