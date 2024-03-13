import os
import re
from dotenv import load_dotenv
import os
import sys

# Load .env file from common subdirectory
load_dotenv(dotenv_path="./common/.env")

# Read the yaml file and replace the OPENAI_API_KEY placeholder
with open("deploy-aci.yaml", "r") as f:
    content = f.read()

vars = [
    "AZURE_STORAGE_ACCOUNT_NAME",
    "AZURE_STORAGE_ACCOUNT_KEY",
    "OPENAI_API_KEY",
    "GOOGLE_GEMINI_KEY",
    "AI_COUNT",
]

# If the AI_COUNT is passed as an argument, set extra environment variables
if len(sys.argv) > 1 and sys.argv[1]:
    os.environ["AI_COUNT"] = str(sys.argv[1])
else:
    os.environ["AI_COUNT"] = "0"
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
    findthing = r'value: "\$\{' + re.escape(var) + r'\}"'
    print("Fixing", var, findthing)
    content = re.sub(
        findthing, f'value: "{os.getenv(var).strip()}"', content, flags=re.MULTILINE
    )

print("Adjusted YAML:\n" + content)

# Write the content to a temporary yaml file
outfile = "temp-deploy-aci.yaml"
with open(outfile, "w") as f:
    f.write(content)

# Run the az container create command
print("Deploying containers...")
print(os.system(f"az container create --resource-group jay --file {outfile}"))

# Delete the temporary yaml file
os.remove(outfile)
