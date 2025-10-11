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
for variable_name in ("MEMORY_COMMANDS_VISIBLE", "SUMMON_COMMAND_VISIBLE", "SPAWN_COMMAND_VISIBLE", "CREATE_COMMAND_VISIBLE"):
    os.environ[variable_name] = "FALSE"

# Initial world expansion
#os.environ["AI_AGENT_FILE_NAME"] = "ai_agents_irp_dev_build_world.json"
#subprocess.call(["python", "agentmanager.py"])

#Clear down any lingering agents from previous experiment
world_name = "normchester"
subprocess.call(["python", "../tools/delete_people_from_db.py", world_name])

os.environ["AI_AGENT_FILE_NAME"] = "ai_agents_irp_dev_join_teams_3.json"

# Set up the AI manager
ai_manager = AIManager(
    model_name="gpt-4o", #os.environ["MODEL_NAME"],
    system_message="You are a helpful AI assistant"
)

# Get list of agents from the file
# Load the list of agents from the JSON file
ai_agent_file = os.environ["AI_AGENT_FILE_NAME"]
agents = []
with open(ai_agent_file, "r") as file:
    data = json.load(file)
    for agent in data["agents"]:
        agents.append(agent["user_name"])
print(f"Loaded {len(agents)} agents from {ai_agent_file}: {', '.join(agents)}")

# Run the subprocess many times
for turn in range(experiment_count):
    print(f"Turn {turn+1}:")
    subprocess.call(["python", "agentmanager.py"])

# Load the session transcript into a string
log_file_pattern = "../orchestrator/logs/*_session_transcript_*.log"
log_files = glob.glob(log_file_pattern)
if log_files:
    log_file_path = max(log_files, key=os.path.getmtime)  # Get the latest file based on modification time
    print(f"Reading from {log_file_path}")
    with open(log_file_path, "r") as log_file:
        print("Session transcript loaded.")
        session_bit = ""
        agent_exclusions = {}
     
        for line in log_file:
            if "thinks:" in line and "I want to team up with":
                team_announcement = line.split("thinks: ", 1)[-1].strip()
                print(team_announcement, flush=True)
                session_bit += team_announcement + "\n"
            # elif "All users have left the world" in line:
            #     ai_request = f"The agents who participated in a team-building experiment are: {', '.join(agents)}. Analyse the users' thoughts below and tell which agent appeared the fewest times as a prospective team-mate. Give me just their name. The data:\n{session_bit}"
            #     #print("Request: ", ai_request)
            #     excluded_agent = ai_manager.submit_request(ai_request, history=False)
            #     print(f"Experiment outcome: {excluded_agent}", flush=True)
            #     agent_exclusions[excluded_agent]=agent_exclusions.get(excluded_agent,0)+1
            #     session_bit = ""
            # Count the number of times each agent is cited as a team-mate
        team_counts = {agent: 0 for agent in agents}
        for line in session_bit.splitlines():
            if "I want to team up with" in line:
                parts = line.split("I want to team up with", 1)[-1].strip()
                team_members = [name.strip() for name in parts.split("and")]
                for member in team_members:
                    if member in team_counts:
                        team_counts[member] += 1

        print("Team counts:", team_counts)
        # Find the agent with the fewest counts
        if team_counts:
            excluded_agent = min(team_counts, key=team_counts.get)
            print(f"The agent with the fewest counts: {excluded_agent}")
        else:
            print("No team counts available.")
        
        #print(agent_exclusions)
else:
    print("Session transcript file not found.")

