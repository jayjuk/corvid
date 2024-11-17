# Set up logger first
from utils import setup_logger
from typing import Dict, Optional, Any, Callable, Tuple
from os import environ
from sys import argv
from os import path, makedirs

logger = setup_logger("gameserver")

from azurestoragemanager import AzureStorageManager
from gamemanager import GameManager


if __name__ == "__main__":

    # Get world name from command line or environment variable
    world_name: str
    if len(argv) > 1:
        world_name = argv[1]
    else:
        world_name = environ.get("GAMESERVER_WORLD_NAME", "jaysgame")

    logger.info(f"Starting up game manager - world '{world_name}'")
    storage_manager: AzureStorageManager = AzureStorageManager()
    game_manager: GameManager = GameManager(
        None,
        storage_manager,
        world_name=world_name,
        model_name=environ.get("MODEL_NAME"),
        image_model_name=environ.get("IMAGE_MODEL_NAME"),
    )

    # Go through all rooms and check if they have an image
    for room_name, room in game_manager.world.rooms.items():
        # print(room_name, room.image)
        if not hasattr(room, "image") or not room.image:
            logger.info(f"Generating image for room {room_name}")

            # Create image for new room
            room.image = game_manager.world.create_room_image(
                room_name, room.description
            )
            storage_manager.store_game_object(game_manager.world.name, room)
            logger.info(f"Generated image for room {room_name} called {room.image}")
