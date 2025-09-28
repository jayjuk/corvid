# Delete world named in command line argument from Azure storage using Azure Storage Manager
import sys
from azurestoragemanager import AzureStorageManager
from room import Room
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
for room in storage_manager.get_world_object_data(args.world, "Room"):
    print(room["name"], room["grid_reference"]), room["exits"])
    #Room exits example: {"west": "Green Grocer", "east": "Rose Lane"}
    #Room grid reference example (string): -2,-6


    #Ignore for now
    #room["grid_reference"] = None
    #o = Room(world=None, init_dict=room)
    #storage_manager.store_world_object(args.world+"_fixed", o)

