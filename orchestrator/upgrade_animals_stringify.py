from storagemanager import StorageManager
import sys

storage_manager = StorageManager()
from animal import Animal
from world import World

w = World()

for o in w.entities.values():
    if o.role == "animal":
        storage_manager.store_world_object("corvid", o)
