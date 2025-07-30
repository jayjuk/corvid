# Set up logger first
import asyncio
from typing import Dict, Optional, Any, Callable, Tuple
from os import environ
from sys import argv
from os import path, makedirs
from utils import set_up_logger, get_critical_env_variable

logger = set_up_logger("generate_missing_images")

from azurestoragemanager import AzureStorageManager
from worldmanager import WorldManager
from messagebroker_helper import MessageBrokerHelper


async def request_room(world_manager, room_name, room_description):
    await world_manager.request_room_image_creation(
        room_name, room_description
    )
    
async def main():
        # Get world name from command line or environment variable
    world_name: str
    if len(argv) > 1:
        world_name = argv[1]
    else:
        world_name = environ.get("ORCHESTRATOR_WORLD_NAME", "corvid")

    # Set up the message broker
    mbh = MessageBrokerHelper(
        get_critical_env_variable("ORCHESTRATOR_HOSTNAME"),
        get_critical_env_variable("ORCHESTRATOR_PORT"),
        {
            # Image creation
            "image_creation_request": {"mode": "publish"},
        },
    )
    logger.info("Message broker set up")

    logger.info(f"Starting up world manager - world '{world_name}'")
    storage_manager: AzureStorageManager = AzureStorageManager()
    world_manager: WorldManager = WorldManager(
        mbh,
        storage_manager,
        world_name=world_name,
        model_name=environ.get("MODEL_NAME"),
    )

    # Ready to Start consuming messages
    await mbh.set_up_nats()

    # Go through all rooms and check if they have an image
    for room_name, room in world_manager.world.rooms.items():
        if room and (not hasattr(room, "image") or not room.image):
            if room.description:
                logger.info(f"Generating image for room {room_name} based on description '{room.description}'. ORCHESTRATOR MUST BE RUNNING for it to be stored.")

                # Create image for new room
                await request_room(world_manager, room_name, room.description)
                await asyncio.sleep(0.2)  # Adjust delay as needed
            else:
                logger.warn(f"Room {room_name} has no description!")


if __name__ == "__main__":

    asyncio.run(main())

