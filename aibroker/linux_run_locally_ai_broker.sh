export AI_COUNT=1
export AI_MODE="agent"
echo Loading env variables from common .env file in local execution...
source ../common/load_dotenv.sh
export MODEL_NAME="llama3-70b-8192"
if [ ! -z "$1" ]; then
    export MODEL_NAME="$1"
fi
echo Running AI Broker with model $MODEL_NAME...
python aibroker.py
