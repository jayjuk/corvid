from storagemanager import StorageManager
from pprint import pprint

storage_manager = StorageManager()

rooms = storage_manager.get_rooms()

print(rooms.keys())
pprint(rooms["Road"])
# for room in rooms.values():
#    print(room["name"])
#    storage_manager.save_new_room_on_cloud(room, "wibbleroom", "wibbledir")
#    exit()
