import os
import subprocess
from dotenv import load_dotenv

# Load environment variables from ../common/.env
load_dotenv("../common/.env")

#Override environment variables
os.environ["AIBROKER_MAX_HISTORY"] = "1000"
os.environ["MODEL_SYSTEM_MESSAGE"] = ""
os.environ["AI_AGENT_FILE_NAME"] = "ai_agents_irp_dev_1.json"

# Run the subprocess 5 times
for turn in range(1):
    print(f"Turn {turn+1}:")
    subprocess.call(["python", "agentmanager.py"])

