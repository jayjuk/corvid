# Delete world named in command line argument from Azure storage using Azure Storage Manager
import sys
from azurestoragemanager import AzureStorageManager
from dotenv import load_dotenv
import os

# Load .env from common folder
full_path = "../common/.env"
# Check if .env file exists in common folder
os.path.exists(full_path) or sys.exit(f"No .env file found at {full_path}")

load_dotenv(dotenv_path=full_path)

# Check world specified
if len(sys.argv) < 2:
    print("Usage: python delete_world_from_db.py <world_name>")
    sys.exit(1)
world_to_delete = sys.argv[1]
asm = AzureStorageManager()
asm.delete_world_from_db(world_to_delete)
