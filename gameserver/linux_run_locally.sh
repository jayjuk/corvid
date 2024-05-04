source ../common/load_dotenv.sh
echo Running Game Server...
export MODEL_NAME="gpt-4-turbo-2024-04-09"
python gameserver.py
