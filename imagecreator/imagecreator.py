# Set up logger first
from typing import Dict, Optional, Tuple
from os import environ
from utils import get_critical_env_variable, connect_to_server, setup_logger, exit
import socketio

# Register the client with the server
sio = socketio.Client()

# Set up logger before importing other modules
# (registers signal handler too hence sio passed in)
logger = setup_logger("Image Creator", sio=sio)

from aimanager import AIManager
from azurestoragemanager import AzureStorageManager


# Class to manage the AI's interaction with the game server
class ImageCreator:

    def __init__(
        self,
        model_name: str = None,
        system_message: Optional[str] = None,
    ) -> None:
        # Constructor

        # Set up the AI manager
        self.ai_manager = AIManager(
            model_name=model_name,
            system_message=system_message,
        )
        # Set up the storage manager
        self.storage_manager: AzureStorageManager = AzureStorageManager()

    def process_work_request(self, data: Dict) -> None:
        logger.info(f"Processing work request: {data}")
        # Do some work here
        logger.info("Work request processed.")

    def create_room_image(
        self, world_name: str, room_name: str, description: str
    ) -> Tuple[bool, Optional[str]]:
        logger.info(
            f"Creating image for room {room_name} with description {description}"
        )

        try:
            image_data: bytes
            image_filename, image_data = self.ai_manager.create_image(
                room_name, description
            )
            if image_data and image_filename:
                return (
                    self.storage_manager.store_image(
                        world_name, image_filename, image_data
                    ),
                    image_filename,
                )
            else:
                logger.error("Error creating/saving image - returned no data")
                return False, image_filename
        except Exception as e:
            logger.error(f"Error creating/saving image ({e})")
            return False, None


# SocketIO event handlers


# Game update event handler
@sio.on("image_creation_request")
def catch_all(data: Dict) -> None:
    logger.info(f"Received image creation request: {data}")
    if data and "room_name" in data and "description" in data:
        # Do some work here
        success, image_filename = image_creator.create_room_image(
            data["world_name"], data["room_name"], data["description"]
        )
        logger.info(f"Image creation success: {success}, filename: {image_filename}")
        # Emit event back to server
        sio.emit(
            "image_creation_response",
            {
                "room_name": data["room_name"],
                "image_filename": image_filename,
                "success": success,
            },
        )

    else:
        exit(logger, "Received invalid event")


# SocketIO event handlers:


# Connection event handler
@sio.event
def connect() -> None:
    logger.info("Connected to Server.")


# Connection error event handler
@sio.event
def connect_error(data: Dict) -> None:
    logger.error(data)


# Disconnection event handler
@sio.event
def disconnect() -> None:
    # TODO #95 Handle reconnection e.g. when Game Server restarts
    logger.info("Disconnected from Server.")


# Main function to start the program
if __name__ == "__main__":

    # Connect to the game server.
    connect_to_server(logger, sio)

    # Create AI Worker
    image_creator = ImageCreator(
        model_name=get_critical_env_variable("IMAGE_MODEL_NAME"),
        system_message=environ.get("MODEL_SYSTEM_MESSAGE"),
    )

    # Check for missing images by emitting missing_image_request
    sio.emit("missing_image_request", {})
    logger.info("Ready...")
    # This keeps the SocketIO event processing going
    sio.wait()
