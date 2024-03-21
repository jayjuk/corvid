from storagemanager import StorageManager
from pprint import pprint

storage_manager = StorageManager()

rooms = storage_manager.get_rooms()

print(rooms.keys())
pprint(rooms["Road"])
# for room in rooms.values():
#    print(room["name"])
#    storage_manager.store_new_room_in_cloud(room, "wibbleroom", "wibbledir")
#    exit()
