source ../common/load_dotenv.sh
echo Running Game Server...
echo Running Game Server... world = $1
# $1 contains world name (optional)
python gameserver.py $1
