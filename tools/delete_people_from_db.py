# Delete world named in command line argument from Azure storage using Azure Storage Manager
import sys
from azurestoragemanager import AzureStorageManager
from dotenv import load_dotenv
import os
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("world", default="normchester")
args = parser.parse_args()

# Load .env from common folder
full_path = "../common/.env"
# Check if .env file exists in common folder
os.path.exists(full_path) or sys.exit(f"No .env file found at {full_path}")

load_dotenv(dotenv_path=full_path)

storage_manager = AzureStorageManager()
print(f"Deleting people from {args.world}")
for person_data in storage_manager.get_world_object_data(args.world, "Person"):
    print(f"Deleting {person_data['name']}")
    storage_manager.delete_world_object(args.world, "Person", person_data["name"])
