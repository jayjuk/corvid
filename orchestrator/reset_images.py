# Script to reset images for all rooms in the world. Takes world name as an argument.

import sys
from azurestoragemanager import AzureStorageManager
from worldmanager import worldmanager
from utils import set_up_logger
from os import environ

# Set up logger
logger = set_up_logger("reset_images")


def reset_images(world_name: str) -> None:
    # Initialize storage manager and world manager
    storage_manager = AzureStorageManager()
    world_manager = worldmanager(
        None,
        storage_manager,
        world_name=world_name,
        model_name=environ.get("MODEL_NAME"),
        image_model_name=environ.get("IMAGE_MODEL_NAME"),
    )

    # Go through all rooms and reset their images
    for room_name, room in world_manager.world.rooms.items():
        logger.info(f"Resetting image for room {room_name}")
        room.image = None
        storage_manager.store_world_object(world_manager.world.name, room)
        logger.info(f"Image for room {room_name} has been reset")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python reset_images.py <world_name>")
        sys.exit(1)

    world_name = sys.argv[1]
    reset_images(world_name)
