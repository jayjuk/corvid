source ../common/load_dotenv.sh
echo Running Game Server...
export MODEL_NAME="gpt-4-turbo"
python gameserver.py
