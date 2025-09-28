from pprint import pprint
from azurestoragemanager import AzureStorageManager
from animal import Animal
from room import Room
from worlditem import WorldItem
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("world", default="normchester")
args = parser.parse_args()

storage_manager = AzureStorageManager()

backup_world_name = f"{args.world}_backup"

storage_manager.delete_world_from_db(backup_world_name)

print("Backing up " + args.world)

for object_type in ("Room", "WorldItem", "Animal"):
    print(f"Backing up type {object_type}")
    objects = storage_manager.get_world_object_data(args.world, object_type)
    for object_data in objects:
            if object_type=="Room":
                o = Room(world=None, init_dict=object_data)
            elif object_type=="WorldItem":
                o = WorldItem(world=None, init_dict=object_data)
            if object_type=="Animal":
                o = Animal(world=None, init_dict=object_data)
            storage_manager.store_world_object(backup_world_name, o)

