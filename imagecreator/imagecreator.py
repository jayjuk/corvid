# Set up logger first
from logger import setup_logger, exit
from typing import Dict, Optional, Tuple
from os import environ
from sys import argv
import time
from os import path, makedirs
from utils import get_critical_env_variable

logger = setup_logger("gameserver")

from aimanager import AIManager
from azurestoragemanager import AzureStorageManager
import socketio
import eventlet

# Set up logger
logger = setup_logger("aibroker")

# Register the client with the server
sio = socketio.Client()


# Class to manage the AI's interaction with the game server
class ImageCreator:

    def __init__(
        self,
        model_name: str = None,
        system_message: Optional[str] = None,
    ) -> None:
        # Constructor
        self.time_to_die = False

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

    def work_loop(self):
        while True:
            # Do some work here
            eventlet.sleep(10)
            logger.info("Waiting for work")


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


# Shutdown event handler
@sio.on("shutdown")
def catch_all(data: Dict) -> None:
    logger.info(f"Shutdown event received: {data}. Exiting immediately.")
    image_creator.time_to_die = True
    sio.disconnect()
    sio.eio.disconnect()
    exit(logger, "Image creator shutting down.")


# Catch all other events
# @sio.on("*")
# def catch_all(event, data: Dict) -> None:
#    pass  # Do nothing


# SocketIO connection handlers


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


# Connect to SocketIO server, trying again if it fails
def connect_to_server(hostname: str) -> None:
    connected: bool = False
    max_wait: int = 240  # 4 minutes
    wait_time: int = 4
    while not connected and wait_time <= max_wait:
        try:
            sio.connect(hostname)
            connected = True
        except Exception as e:
            logger.info(
                f"Could not connect to server. Retrying in {wait_time} seconds..."
            )
            eventlet.sleep(wait_time)
            wait_time = int(wait_time * 2)

    if not connected:
        exit(logger, "Could not connect to Game Server. Is it running?")


# Main function to start the program
if __name__ == "__main__":
    # Set up logging to file and console
    logger.info("Starting up Game AI Worker")

    # Change log file name to include AI name
    logger = setup_logger("game_worker.log")

    # Set hostname (default is "localhost" to support local pre container testing)
    # hostname = socket.getfqdn()
    # if hostname.endswith(".lan"):
    #     hostname = hostname[:-4]
    hostname: str = environ.get("GAMESERVER_HOSTNAME") or "localhost"
    # TODO #65 Do not allow default port, and make this common
    port: str = environ.get("GAMESERVER_PORT", "3001")
    logger.info(f"Starting up Game AI Worker on hostname {hostname}")
    # Connect to the server. If can't connect, warn user that the Game Server may not be running.
    try:
        connect_to_server(f"http://{hostname}:{port}")
    except Exception as e:
        exit(logger, f"Could not connect to server: {e}\nIs the Game Server running?")
    logger.info("Connected to server.")
    # Create AI Worker
    image_creator = ImageCreator(
        model_name=get_critical_env_variable("IMAGE_MODEL_NAME"),
        system_message=environ.get("MODEL_SYSTEM_MESSAGE"),
    )

    # Check for missing images by emitting missing_image_request
    sio.emit("missing_image_request", {})

    # This is where the main processing of inputs happens
    eventlet.spawn(image_creator.work_loop())

    # This keeps the SocketIO event processing going
    sio.wait()
