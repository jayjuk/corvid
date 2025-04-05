from storagemanager import StorageManager
from worlditem import WorldItem

storage_manager = StorageManager()

# for object_data in storage_manager.get_objects():
#     print(object_data)
#     o = Object(world_ref=None, init_dict=object_data)
#     storage_manager.store_world_object("corvid", o)

for object_data in storage_manager.get_world_objects("corvid", "Object"):
    print(object_data)
    o = WorldItem(world=None, init_dict=object_data)
    # Re-store object with latest method
    storage_manager.store_world_object("corvid", o)
