import os
import subprocess
from dotenv import load_dotenv
import glob
from aimanager import AIManager
import json
import argparse

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Run AI Broker experiment.")
parser.add_argument("--experiment_count", type=int, default=0, help="Number of experiment turns to run (default: 0)")
args = parser.parse_args()

experiment_count = args.experiment_count
# Load environment variables from ../common/.env
load_dotenv("../common/.env")

#Override environment variables
os.environ["AIBROKER_MAX_HISTORY"] = "200"
os.environ["MODEL_SYSTEM_MESSAGE"] = ""
os.environ["AI_MANAGER_LOGGING_LEVEL"] = "WARNING"

# Disabling summon mode means that the agent manager exits when all its AI brokers have exited.
os.environ["AGENT_MANAGER_SUMMON_MODE"] = "FALSE"
os.environ["ALLOW_SOLO_AGENT_ACTIVITY"] = "TRUE"

# Set a bunch of flags - for now hide these commands
for variable_name in ("MEMORY_COMMANDS_VISIBLE", "SUMMON_COMMAND_VISIBLE", "SPAWN_COMMAND_VISIBLE", "CREATE_COMMAND_VISIBLE", "THINK_COMMAND_VISIBLE"):
    os.environ[variable_name] = "FALSE"

# Initial world expansion
#os.environ["AI_AGENT_FILE_NAME"] = "ai_agents_irp_dev_build_world.json"
#subprocess.call(["python", "agentmanager.py"])

os.environ["AI_AGENT_FILE_NAME"] = "ai_agents_irp_dev_join_teams_4.json"

# Get list of agents from the file
# Load the list of agents from the JSON file
ai_agent_file = os.environ["AI_AGENT_FILE_NAME"]
agents = []
with open(ai_agent_file, "r") as file:
    data = json.load(file)
    for agent in data["agents"]:
        agents.append(agent["user_name"])
print(f"Loaded {len(agents)} agents from {ai_agent_file}: {', '.join(agents)}")

if experiment_count:
    #Clear down any lingering agents from previous experiment
    world_name = "normchester"
    subprocess.call(["python", "../tools/delete_people_from_db.py", world_name])

    # Spawn an orchestrator, redirecting stdout and stderr to a log file, and remembering the PID to kill it later
    log_file_path = os.path.join("../orchestrator/logs", "orchestrator_output.log")
    os.environ["SHUT_DOWN_ON_EMPTY"]="TRUE"
    with open(log_file_path, "a") as log_file:
        orchestrator_process = subprocess.Popen(
            ["python", "orchestrator.py", world_name],
            cwd="../orchestrator",  # Change working directory to the orchestrator folder
            stdout=log_file,  # Redirect standard output to the log file
            stderr=log_file   # Redirect standard error to the log file
        )

    # Run the subprocess many times
    for turn in range(experiment_count):
        print(f"Turn {turn+1}:")
        subprocess.call(["python", "agentmanager.py"])
    
    # Wait for orchestrator to shut down once last agent leaves
    #orchestrator_process.terminate()
    print("Waiting for orchestrator to shut itself down...")
    orchestrator_process.wait()
    print("Finished!")


# Set up the AI manager
ai_manager = AIManager(
    model_name="gpt-5-mini", #os.environ["MODEL_NAME"],
    system_message="You are a helpful AI assistant"
)
print("Test:", ai_manager.submit_request("Respond with just OK"))

# Load the session transcript into a string
log_file_pattern = "../orchestrator/logs/*_session_transcript_*.log"
log_files = glob.glob(log_file_pattern)
if log_files:
    log_file_path = max(log_files, key=os.path.getmtime)  # Get the latest file based on modification time
    print(f"Reading from {log_file_path}")
    try:
        with open(log_file_path, "r") as log_file:
            print("Session transcript loaded.")
            log_content = "\n".join(line for line in log_file if "join your team" in line or "All users have left the world." in line)  # Filter lines containing ': say'
    except Exception as e:
        print(f"Error reading log file: {e}")
        log_content = ""
    if log_content:

        ai_request = f"Analyse the experiment transcript below and tell how many times in total each team leader (Andy, Chris and Mohammed) was chosen by another user. Note that there may be multiple sessions in the one log, separated by the line 'All users have left the world.'. The data:\n{log_content}"
        print("Request: ", ai_request)
        print("Outcome:", ai_manager.submit_request(ai_request, temperature=1))
    else:
        print("Log contents not found.")
else:
    print("Session transcript file not found.")

