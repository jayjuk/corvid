import os
import re
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# Get the OpenAI key
openai_key = os.getenv("OPENAI_KEY").strip()

# Read the yaml file and replace the OPENAI_API_KEY placeholder
with open("deploy-aci.yaml", "r") as f:
    content = f.read()

# Set env variable AI_COUNT to 1
os.environ["AI_COUNT"] = "1"

for var in (
    "AZURE_STORAGE_ACCOUNT_NAME",
    "AZURE_STORAGE_ACCOUNT_KEY",
    "OPENAI_API_KEY",
    "AI_COUNT",
):
    content = re.sub(rf"value: \${var}", f"value: {os.getenv(var).strip()}", content)

# Write the content to a temporary yaml file
with open("temp-deploy-aci-ai.yaml", "w") as f:
    f.write(content)

# Run the az container create command
os.system("az container create --resource-group jay --file temp-deploy-aci-ai.yaml")

# Delete the temporary yaml file
os.remove("temp-deploy-aci-ai.yaml")
