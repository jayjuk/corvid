from storagemanager import StorageManager
import sys

storage_manager = StorageManager()
# first arg is room name
room_name = sys.argv[1]
if room_name:
    print(f"Deleting room {room_name} from cloud")
    storage_manager.delete_room_in_cloud(room_name)
    print(f"Deleting room {room_name} from local storage")
    storage_manager.delete_room_locally(room_name)
else:
    print("No room name provided (arg 1 in double quotes)")
    sys.exit()
