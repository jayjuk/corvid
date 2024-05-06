source ../common/load_dotenv.sh
echo Running Game Server...
export MODEL_NAME="gpt-4-turbo"
# If param set, use that as model name
if [ -n "$1" ]; then
  echo "Using model name: $1"
  export MODEL_NAME=$1
fi
python gameserver.py
