import storagemanager
from pprint import pprint

rooms = storagemanager.get_rooms()

print(rooms.keys())
pprint(rooms["Road"])
# for room in rooms.values():
#    print(room["name"])
#    storagemanager.save_new_room_on_cloud(room, "wibbleroom", "wibbledir")
#    exit()
