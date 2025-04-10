# Set up logger first
from utils import set_up_logger
from typing import Dict, Optional, Any, Callable, Tuple
from os import environ
from sys import argv
from os import path, makedirs

logger = set_up_logger("orchestrator")

from azurestoragemanager import AzureStorageManager
from worldmanager import WorldManager


if __name__ == "__main__":

    # Get world name from command line or environment variable
    world_name: str
    if len(argv) > 1:
        world_name = argv[1]
    else:
        world_name = environ.get("ORCHESTRATOR_WORLD_NAME", "corvid")

    logger.info(f"Starting up world manager - world '{world_name}'")
    storage_manager: AzureStorageManager = AzureStorageManager()
    world_manager: WorldManager = WorldManager(
        None,
        storage_manager,
        world_name=world_name,
        model_name=environ.get("MODEL_NAME"),
        image_model_name=environ.get("IMAGE_MODEL_NAME"),
    )

    # Go through all rooms and check if they have an image
    for room_name, room in world_manager.world.rooms.items():
        # print(room_name, room.image)
        if not hasattr(room, "image") or not room.image:
            logger.info(f"Generating image for room {room_name}")

            # Create image for new room
            room.image = world_manager.world.create_room_image(
                room_name, room.description
            )
            storage_manager.store_world_object(world_manager.world.name, room)
            logger.info(f"Generated image for room {room_name} called {room.image}")
