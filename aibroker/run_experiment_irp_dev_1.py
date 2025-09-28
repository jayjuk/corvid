import os
import subprocess
from dotenv import load_dotenv
import glob
from aimanager import AIManager
import json

# Load environment variables from ../common/.env
load_dotenv("../common/.env")

#Override environment variables
os.environ["AIBROKER_MAX_HISTORY"] = "200"
os.environ["MODEL_SYSTEM_MESSAGE"] = ""
os.environ["AI_MANAGER_LOGGING_LEVEL"] = "WARNING"
# Disabling summon mode means that the agent manager exits when all its AI brokers have exited.
os.environ["AGENT_MANAGER_SUMMON_MODE"] = "FALSE"

# Set a bunch of flags - for now hide these commands
for variable_name in ("MEMORY_COMMANDS_VISIBLE", "SUMMON_COMMAND_VISIBLE", "SPAWN_COMMAND_VISIBLE", "CREATE_COMMAND_VISIBLE"):
    os.environ[variable_name] = "FALSE"

# Initial world expansion
#os.environ["AI_AGENT_FILE_NAME"] = "ai_agents_irp_dev_build_world.json"
#subprocess.call(["python", "agentmanager.py"])

#Clear down any lingering agents from previous experiment
world_name = "normchester"
subprocess.call(["python", "../tools/delete_people_from_db.py", world_name])

os.environ["AI_AGENT_FILE_NAME"] = "ai_agents_irp_dev_join_teams_1.json"
experiment_number = 100

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
    for agent in data["people"]:
        agents.append(agent["user_name"])
print(f"Loaded {len(agents)} agents from {ai_agent_file}: {', '.join(agents)}")

# Run the subprocess many times
for turn in range(experiment_number):
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
            if "shout WE ARE TEAM" in line:
                team_announcement = line.split("WE ARE TEAM ", 1)[-1].strip()
                #print(team_announcement, flush=True)
                session_bit += team_announcement + "\n"
            elif ": mission_accomplished" in line:
                ai_request = f"The agents who participated in a team-building experiment are: {', '.join(agents)}. Analyse the team membership announcements below and tell which agent was not mentioned in any team. Give me just their name. If all agents were mentioned, respond with Error. The data:\n{session_bit}"
                #print("Request: ", ai_request)
                excluded_agent = ai_manager.submit_request(ai_request, history=False)
                print(f"Experiment outcome: {excluded_agent}", flush=True)
                agent_exclusions[excluded_agent]=agent_exclusions.get(excluded_agent,0)+1
                session_bit = ""
        
        print(agent_exclusions)
else:
    print("Session transcript file not found.")

