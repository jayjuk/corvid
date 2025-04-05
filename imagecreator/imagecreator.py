import asyncio
from typing import Dict, Optional, Tuple
import os
from utils import get_critical_env_variable, set_up_logger, exit

# Set up logger before importing other modules
logger = set_up_logger("Image Creator")
from messagebroker_helper import MessageBrokerHelper
from aimanager import AIManager
from azurestoragemanager import AzureStorageManager
import random
from PIL import Image


# Class to manage the AI's interaction with the Orchestrator
class ImageCreator:

    def __init__(
        self,
        mbh: MessageBrokerHelper,
        image_model_name: str = None,
        text_model_name: str = None,
        system_message: Optional[str] = None,
        landscape: Optional[str] = None,
    ) -> None:
        # Constructor
        self.landscape = landscape
        self.mbh = mbh

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
            test_response = self.text_ai_manager.submit_request(
                "Checking connectivity - if you got this, respond with just 'OK'.",
                history=False,
            )
            logger.info(f"Text model test response: {test_response}")
        else:
            self.text_ai_manager = None
            logger.info("No text model provided: text AI manager not set up")

        # Set up the storage manager
        self.storage_manager: AzureStorageManager = AzureStorageManager()

    async def process_image_request(self, data: Dict) -> None:
        logger.info(f"Processing work request: {data}")

        if data and "room_name" in data and "description" in data:
            # Do some work here
            success, image_filename = self.create_room_image(
                data["world_name"],
                data["room_name"],
                data["description"],
                data.get("landscape", self.landscape),
            )
            logger.info(
                f"Image creation success: {success}, filename: {image_filename}"
            )
            # Emit event back to server
            await self.mbh.publish(
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
            f"Convert the following world location description into a more suitable concise prompt for an AI image generation model. The style is '{art_style}',"
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
        image_filename: Optional[str] = None
        image_data: Optional[bytes] = None
        if os.environ.get("TEST_MODE", "False").upper() == "TRUE":
            logger.info("TEST_MODE is enabled, generating a random image locally")
            try:

                # Generate a random image
                width, height = 256, 256
                image = Image.new(
                    "RGB",
                    (width, height),
                    (
                        random.randint(0, 255),
                        random.randint(0, 255),
                        random.randint(0, 255),
                    ),
                )
                # Save the image to a file temporarily
                image_filename = f"{room_name}_test_image.png"
                image_path = f"{image_filename}"
                image.save(image_path)
                logger.info(f"Random test image created: {image_path}")

                with open(image_path, "rb") as image_file:
                    image_data = image_file.read()
                # Remove file
                os.remove(image_path)

            except Exception as e:
                logger.error(f"Error generating random test image ({e})")
                return False, None
        else:
            if self.text_ai_manager:
                # Convert the description into a more suitable prompt for image generation
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
                logger.info(f"AI Image created: {image_filename}")
            except Exception as e:
                logger.error(f"Error creating/saving image ({e})")
                return False, None

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


async def main() -> None:
    async def process_image_request(data: Dict) -> None:
        logger.info(f"Received image creation request: {data}")
        await image_creator.process_image_request(data)

    mbh = MessageBrokerHelper(
        os.environ.get("orchestrator_HOSTNAME", "localhost"),
        os.environ.get("orchestrator_PORT", 4222),
        {
            "image_creation_response": {"mode": "publish"},
            "image_creation_request": {
                "mode": "subscribe",
                "callback": process_image_request,
            },
        },
    )

    # Create AI Worker
    image_creator = ImageCreator(
        mbh=mbh,
        image_model_name=get_critical_env_variable("IMAGE_MODEL_NAME"),
        text_model_name=get_critical_env_variable("MODEL_NAME"),
        system_message=os.environ.get("MODEL_SYSTEM_MESSAGE"),
        landscape=os.environ.get("LANDSCAPE_DESCRIPTION"),
    )

    # Start consuming messages
    await mbh.set_up_nats()

    await asyncio.Event().wait()  # Keeps the event loop running


# Main function to start the program
if __name__ == "__main__":
    asyncio.run(main())
