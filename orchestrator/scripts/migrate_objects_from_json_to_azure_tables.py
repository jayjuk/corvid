from storagemanager import StorageManager

storage_manager = StorageManager()

objects = storage_manager.get_default_objects()

for object in objects:
    storage_manager.store_object(object)
