import os
import re
from dotenv import load_dotenv
import os
import sys

# Load .env file from gameserver subdirectory
load_dotenv(dotenv_path="./gameserver/.env")
# Load .env file from aibroker subdirectory (does not overwrite existing env vars)
load_dotenv(dotenv_path="./aibroker/.env")

# Read the yaml file and replace the OPENAI_API_KEY placeholder
with open("deploy-aci.yaml", "r") as f:
    content = f.read()

vars = [
    "AZURE_STORAGE_ACCOUNT_NAME",
    "AZURE_STORAGE_ACCOUNT_KEY",
]

# If the AI_COUNT is passed as an argument, set extra environment variables
if len(sys.argv) > 1 and sys.argv[1]:
    os.environ["AI_COUNT"] = str(sys.argv[1])
    vars.append("OPENAI_API_KEY")
    vars.append("AI_COUNT")
else:
    print("No AI - removing that container from the yaml file")
    # Remove the lines from name: aibroker (inclusive) to osType: Linux (exclusive)
    content = re.sub(
        r"    - name: aibroker.*osType: Linux",
        "osType: Linux",
        content,
        flags=re.MULTILINE | re.DOTALL,
    )


# Replace the placeholders with the environment variables
for var in vars:
    content = re.sub(rf"value: \${var}", f"value: {os.getenv(var).strip()}", content)

# Write the content to a temporary yaml file
with open("temp-deploy-aci-ai.yaml", "w") as f:
    f.write(content)

# Run the az container create command
print("Deploying containers...")
print(
    os.system("az container create --resource-group jay --file temp-deploy-aci-ai.yaml")
)

# Delete the temporary yaml file
os.remove("temp-deploy-aci-ai.yaml")
