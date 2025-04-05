source ../common/load_dotenv.sh
echo Running Orchestrator...
echo Running Orchestrator... world = $1
# $1 contains world name (optional)
python orchestrator.py $1
