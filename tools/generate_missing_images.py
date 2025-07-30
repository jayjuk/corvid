from typing import List, Tuple
from orchestrator.world import World
from utils import set_up_logger
from orchestrator.world import World

# Set up logger
logger = set_up_logger()

def fix_missing_images(world: World, publish_message: callable) -> None:
    """
    Fix missing images in a world by publishing messages to an image creator service.

    Args:
        world (World): The world object to check for missing images.
        publish_message (callable): A function to publish messages to the image creator service.
    """
    logger.info(f"Checking for missing images in world: {world.get_name()}")

    # Get rooms missing images
    rooms_missing_images: List[Tuple[str, str]] = world.get_rooms_missing_images()

    if not rooms_missing_images:
        logger.info("No rooms are missing images.")
        return

    logger.info(f"Found {len(rooms_missing_images)} rooms missing images.")

    for room_name, room_description in rooms_missing_images:
        # Create a message for the image creator
        message = {
            "room_name": room_name,
            "description": room_description,
            "world_name": world.get_name(),
        }

        try:
            # Publish the message to the image creator service
            publish_message(message)
            logger.info(f"Published image creation request for room: {room_name}")
        except Exception as e:
            logger.error(f"Failed to publish image creation request for room {room_name}: {e}")


# Assume `world` is an instance of the World class
world = World(name="jaysgame", storage_manager=None)

# Define a mock publish_message function for testing
def mock_publish_message(message):
    print(f"Publishing message: {message}")

# Fix missing images
fix_missing_images(world, mock_publish_message)
