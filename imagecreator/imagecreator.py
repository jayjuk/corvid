import eventlet

eventlet.monkey_patch()

import socketio
import logging
from queue import Queue
from threading import Thread

# Set up logger first
from typing import Dict, Optional, Tuple
from os import environ
from utils import get_critical_env_variable, connect_to_server, setup_logger, exit

# Register the client with the server
sio = socketio.Client()

# Set up logger before importing other modules
# (registers signal handler too hence sio passed in)
logger = setup_logger("Image Creator", sio=sio)

from aimanager import AIManager
from azurestoragemanager import AzureStorageManager

# Create a queue to hold events
event_queue = Queue()


# Class to manage the AI's interaction with the game server
class ImageCreator:

    def __init__(
        self,
        image_model_name: str = None,
        text_model_name: str = None,
        system_message: Optional[str] = None,
        landscape: Optional[str] = None,
    ) -> None:
        # Constructor
        self.landscape = landscape

        # Set up the AI managers
        self.image_ai_manager = AIManager(
            model_name=image_model_name,
            system_message=system_message,
        )
        if text_model_name:
            if text_model_name == image_model_name:
                logger.info(
                    "Text and image models are the same: using the same AI manager"
                )
                self.text_ai_manager = self.image_ai_manager
            else:
                self.text_ai_manager = AIManager(
                    model_name=text_model_name,
                    system_message=system_message,
                )
            test_response = self.text_ai_manager.submit_request("ping", history=False)
            logger.info(f"Text model test response: {test_response}")
        else:
            self.text_ai_manager = None
            logger.info("No text model provided: text AI manager not set up")

        # Set up the storage manager
        self.storage_manager: AzureStorageManager = AzureStorageManager()

    # Function to process events from the queue
    def process_events(self) -> None:
        while True:
            event, data = event_queue.get()
            try:
                if event == "work_request":
                    self.process_work_request(data)
                # Add more event types as needed
            except Exception as e:
                logger.error(f"Error processing event {event}: {e}")
            finally:
                event_queue.task_done()

    def process_work_request(self, data: Dict) -> None:
        logger.info(f"Processing work request: {data}")

        if data and "room_name" in data and "description" in data:
            # Do some work here
            success, image_filename = image_creator.create_room_image(
                data["world_name"],
                data["room_name"],
                data["description"],
                data.get("landscape", image_creator.landscape),
            )
            logger.info(
                f"Image creation success: {success}, filename: {image_filename}"
            )
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

        logger.info("Work request processed.")

    def convert_description_to_prompt(
        self, world_name: str, description: str, landscape: str
    ) -> str:
        # Convert the description into a more suitable prompt for image generation
        art_style = "Fantasy Art"
        if landscape:
            world_theme = landscape
        else:
            logger.info(
                f"No landscape provided: more basic world name '{world_name}' used"
            )
            world_theme = world_name
        instruction = (
            f"Convert the following game location description into a more suitable concise prompt for an AI image generation model. The style is '{art_style}',"
            + f" and the overarching world is '{world_theme}'."
            + f" Description:\n{description}"
        )
        try:
            response = self.text_ai_manager.submit_request(
                request=instruction, history=False, cleanup_output=False
            )
            logger.info(f"Response from text AI manager: {response}")
            return response
        except Exception as e:
            logger.error(f"Error generating prompt ({e})")
            return ""

    def create_room_image(
        self,
        world_name: str,
        room_name: str,
        description: str,
        landscape: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        logger.info(
            f"Creating image for room {room_name} with description {description}"
        )

        # Convert the description into a more suitable prompt for image generation
        if self.text_ai_manager:
            try:
                prompt = self.convert_description_to_prompt(
                    world_name, description, landscape
                )
                logger.info(f"Generated better prompt for image creation: {prompt}")
            except Exception as e:
                logger.error(f"Error generating prompt ({e})")
                return False, None
        else:
            prompt = description + "\n Background context: " + landscape
            logger.info("Using original description as prompt for image creation")

        try:
            image_data: bytes
            image_filename, image_data = self.image_ai_manager.create_image(
                room_name, prompt
            )
            logger.info(f"Image created: {image_filename}")
            # Output length of image data in bytes
            logger.info(f"Image data length: {len(image_data)} bytes")
            if image_data and image_filename:
                logger.info("Saving image to storage")
                return (
                    self.storage_manager.store_image(
                        world_name, image_filename, image_data
                    ),
                    image_filename,
                )
            else:
                logger.error("Error creating/saving image - returned no data")
                return (False, image_filename)
        except Exception as e:
            logger.error(f"Error creating/saving image ({e})")
            return False, None


# SocketIO event handlers


# Game update event handler
@sio.on("image_creation_request")
def catch_all(data: Dict) -> None:
    logger.info(f"Received image creation request: {data}")
    # Add to queue
    event_queue.put(("work_request", data))


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
        image_model_name=get_critical_env_variable("IMAGE_MODEL_NAME"),
        text_model_name=get_critical_env_variable("MODEL_NAME"),
        system_message=environ.get("MODEL_SYSTEM_MESSAGE"),
        landscape=environ.get("LANDSCAPE_DESCRIPTION"),
    )

    # Start the worker thread
    worker_thread = Thread(target=image_creator.process_events)
    worker_thread.daemon = True
    worker_thread.start()

    # Check for missing images by emitting missing_image_request
    sio.emit("missing_image_request", {})

    logger.info("Ready...")

    # This keeps the SocketIO event processing going
    sio.wait()
