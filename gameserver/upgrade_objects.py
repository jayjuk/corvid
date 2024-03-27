from storagemanager import StorageManager
import sys

storage_manager = StorageManager()
from object import Object

for object_data in storage_manager.get_objects():
    print(object_data)
    o = Object(world=None, init_dict=object_data)
    storage_manager.store_game_object("jaysgame", o)

for object_data in storage_manager.get_game_objects("jaysgame", "Object"):
    print(object_data)
    # o = Object(world_ref=None, init_dict=object_data)
    # storage_manager.store_game_object("jaysgame", o)
