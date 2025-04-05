from storagemanager import StorageManager
import sys

storage_manager = StorageManager()
from room import Room

for room in storage_manager.get_game_objects("mansion", "Room"):

    # print(room["image"])
    # b = storage_manager.get_image_blob(room["image"])
    # if b:
    #     storage_manager.store_image("corvid", f"corvid.{room['image']}", b)
    print(room)
    if room["name"] in ("Hall", "Kitchen"):
        b = storage_manager.get_image_blob(room["image"])
        if b:
            storage_manager.store_image("mansion", f"mansion.{room['image']}", b)
