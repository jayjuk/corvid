source ../common/load_dotenv.sh
if [ -z "$1" ]; then
    AI_AGENT_FILE_NAME="ai_agents.json"
else
    AI_AGENT_FILE_NAME="$1"
fi
python agentmanager.py
