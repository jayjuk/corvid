source ../common/load_dotenv.sh
if [ -z "$1" ]; then
    AI_PLAYER_FILE_NAME="no_ai_players.json"
else
    AI_PLAYER_FILE_NAME="$1"
fi
python playermanager.py
