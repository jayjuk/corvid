import os
import re
from dotenv import load_dotenv
import os
import sys

# Load .env file from common subdirectory
load_dotenv(dotenv_path="./common/.env")


def do_deploy(deploy_file: str) -> None:

    with open(deploy_file, "r") as f:
        content = f.read()

    # If the AI_COUNT is passed as an argument, set extra environment variables
    if len(sys.argv) > 2 and sys.argv[1]:
        os.environ["AI_COUNT"] = str(sys.argv[2])
    elif "AI_COUNT" not in os.environ:
        os.environ["AI_COUNT"] = "0"

    if os.environ["AI_COUNT"] == "0":
        print("AI COUNT resolved to 0 - removing that container from the yaml file")
        # Remove the lines from name: aibroker (inclusive) to osType: Linux (exclusive)
        content = re.sub(
            r"    - name: aibroker.*osType: Linux",
            "  osType: Linux",
            content,
            flags=re.MULTILINE | re.DOTALL,
        )

    # Replace the placeholders with the environment variables by going through each line,
    # Changing ${GAMESERVER_WORLD_NAME} to the value of the environment variable GAMESERVER_WORLD_NAME etc
    new_content = ""
    for line in content.split("\n"):
        # Assume only one placeholder per line
        match = re.search(r"\$\{(\w+)\}", line)
        if match:
            var = match.group(1)
            new_value = os.getenv(var, "")
            print(f"Replacing ${var} with {new_value}")
            line = line.replace(f"${{{var}}}", new_value)
        new_content += line + "\n"
    content = new_content

    # Write the content to a temporary yaml file
    outfile = "temp-" + deploy_file
    with open(outfile, "w") as f:
        f.write(content)

    # Run the az container create command
    print("Deploying containers...")
    print(os.system(f"az container create --resource-group jay --file {outfile}"))

    # Delete the temporary yaml file
    print("Cleaning up...")
    os.remove(outfile)


# Run the script
if __name__ == "__main__":
    # Get arg0
    if len(sys.argv) > 1:
        do_deploy(sys.argv[1])
    else:
        print(
            "Usage: python az-deploy.py deploy-aci.yaml (YAML file) [0 (number of AIs, or use AI_COUNT in .env)]"
        )
        sys.exit(1)
