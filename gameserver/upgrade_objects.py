from storagemanager import StorageManager

storage_manager = StorageManager()
from gameitem import GameItem

for object_data in storage_manager.get_objects():
    print(object_data)
    o = GameItem(world=None, init_dict=object_data)
    storage_manager.store_game_object("corvid", o)

for object_data in storage_manager.get_game_objects("corvid", "Object"):
    print(object_data)
    # o = Object(world_ref=None, init_dict=object_data)
    # storage_manager.store_game_object("corvid", o)
