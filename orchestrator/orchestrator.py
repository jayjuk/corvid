# Set up logger first
from utils import set_up_logger, exit, get_logs_folder, get_critical_env_variable
from typing import Dict, Optional, Any, Callable, Tuple
from os import environ
from sys import argv
import time
from os import path, makedirs
import asyncio

# Set up logger before importing other own modules
logger = set_up_logger("Orchestrator")

from azurestoragemanager import AzureStorageManager
from worldmanager import WorldManager
from person import Person
from user_input_processor import UserInputProcessor
from messagebroker_helper import MessageBrokerHelper
from shutdownexception import ShutdownException


class Orchestrator:
    """Manage interactions between Front End / AI agents and all the back-end services"""

    # Transcript management

    # Create a log file for model responses
    def get_user_transcript_file_handle(self, user_name: str) -> str:
        if user_name not in self.user_transcripts:
            # Create a new log file for the user and return a handle to it
            makedirs(get_logs_folder(), exist_ok=True)
            f = open(path.join(get_logs_folder(), f"{user_name}_world_transcript.txt"))
            f.write(f"# Person input and response log for {user_name}\n\n")
            self.user_transcripts[user_name] = f
        return self.user_transcripts[user_name]

    # Log model response to file
    # TODO #111 Improve transcript logging to capture everything the user sees
    def log_to_user_transcript(
        self, user_name: str, request: str = "", response: str = ""
    ) -> None:
        timestamp: str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        f = self.get_user_transcript_file_handle(user_name)
        f.write(f"{timestamp} {user_name}: {request}\n")
        f.write(f"{timestamp} World: {response}\n\n")

    # Event handlers

    # Person setup
    async def set_user_name(self, user_info: Dict[str, str]) -> None:
        user_id: str = user_info["user_id"]
        logger.info(
            f"Client requesting person setup: {user_id}, {user_info.get('name')}, {user_info.get('role')}"
        )
        outcome: Optional[str] = await self.world_manager.process_user_setup(
            user_id, user_info, self.user_input_processor.get_help_text()
        )
        # Blank outcome = success
        if outcome:
            # Issue with person name setting - indicate using name_invalid event, with error message
            await self.mbh.publish(
                "name_invalid",
                outcome,
                user_id,
            )
        else:
            self.create_user_transcript(user_info.get("name"))

    # User action
    async def user_action(self, data: Dict[str, str]):
        user_id: str = data["user_id"]
        user_input: str = data["user_input"]

        if user_id in self.world_manager.people:
            person: Person = self.world_manager.people[user_id]
            logger.info(
                f"Received user action: {user_input} from {user_id} ({person.name})"
            )
            await self.mbh.publish("world_update", f"You: {user_input}", user_id)
            command_function: Callable
            command_args: Tuple
            response_to_person: Optional[str]

            # Process person input to resolve the command and arguments, or return an error message
            result = await self.user_input_processor.process_user_input(
                person, user_input
            )
            (command_function, command_args, response_to_person) = result
            if command_function:
                if isinstance(command_function, Callable):
                    logger.info(
                        f"Command function: {command_function.__name__}, Args: {command_args}"
                    )
                    if asyncio.iscoroutinefunction(command_function):
                        response_to_person = await command_function(*command_args)
                    else:
                        response_to_person = command_function(*command_args)
                else:
                    exit(
                        logger,
                        f"Command function not found for input: {user_input}, command_function = {command_function}",
                    )

            # Respond to person
            if response_to_person:
                person.add_input_history(f"World: {response_to_person}")
                await self.mbh.publish("world_update", response_to_person, user_id)

            # Log person input and response
            self.log_to_user_transcript(person.name, user_input, response_to_person)
        else:
            logger.info(f"Received user action from non-existent person {user_id}")
            await self.mbh.publish(
                "logout",
                "You have been logged out due to a server error. Please log in again.",
                user_id,
            )

    # Disconnection
    def user_disconnect(self, data: Dict[str, str]) -> None:
        user_id: str = data["user_id"]
        logger.info(f"Client disconnected: {user_id}")
        # TODO #72 Allow people to reconnect (for now disconnect is same as quit)
        self.world_manager.remove_person(
            user_id, "You have been logged out as your client disconnected."
        )

    async def image_creation_response(self, data: Dict) -> None:
        logger.info(f"Received image creation response: {data}")
        await self.world_manager.process_image_creation_response(
            data["room_name"], data["image_filename"], data["success"]
        )

    async def summon_agent_response(self, data: Dict) -> None:
        logger.info(f"Received summon person response: {data}")
        await self.world_manager.process_summon_agent_response(data["request_id"])

    async def ai_response(self, data: Dict) -> None:
        logger.info(f"Received AI response: {data}")
        if (
            "request_id" in data
            and data["request_id"] in self.world_manager.ai_manager.remote_requests
        ):
            # TODO #98 should Orchestrator be allowed to access ai manager directly?
            person: Person
            response_to_person: str
            (person, response_to_person) = (
                await self.world_manager.ai_manager.process_ai_response(data)
            )
            if response_to_person:
                person.add_input_history(f"World: {response_to_person}")
                await self.mbh.publish(
                    "world_update", response_to_person, person.user_id
                )
                logger.info(
                    f"Emitting this response from the handler of this response: {response_to_person}"
                )

            # Log person input and response
            self.log_to_user_transcript(
                person.name, "[AI response]", response_to_person
            )

        else:
            exit(logger, f"Valid request ID not found: data {data}")

    # End of event handlers

    # Constructor
    def __init__(self, world_name: str) -> None:

        # Set up the message broker
        logger.info("Setting up message broker")
        self.mbh = MessageBrokerHelper(
            get_critical_env_variable("ORCHESTRATOR_HOSTNAME"),
            get_critical_env_variable("ORCHESTRATOR_PORT"),
            {
                # Client messages
                "instructions": {"mode": "publish"},
                "name_invalid": {"mode": "publish"},
                "room_update": {"mode": "publish"},
                "world_update": {"mode": "publish"},
                "world_data_update": {"mode": "publish"},
                "logout": {"mode": "publish"},
                # Image creation
                "image_creation_request": {"mode": "publish"},
                "image_creation_response": {
                    "mode": "subscribe",
                    "callback": self.image_creation_response,
                },
                # General AI requests
                "ai_request": {"mode": "publish"},
                "ai_response": {"mode": "subscribe", "callback": self.ai_response},
                # Summon person
                "summon_agent_request": {"mode": "publish"},
                "summon_agent_response": {
                    "mode": "subscribe",
                    "callback": self.summon_agent_response,
                },
                "user_disconnect": {
                    "mode": "subscribe",
                    "callback": self.user_disconnect,
                },
                "set_user_name": {"mode": "subscribe", "callback": self.set_user_name},
                "user_action": {"mode": "subscribe", "callback": self.user_action},
            },
        )
        logger.info("Message broker set up")

        logger.info(f"Starting up world manager - world '{world_name}'")
        storage_manager: AzureStorageManager = AzureStorageManager()
        self.world_manager: WorldManager = WorldManager(
            self.mbh,
            storage_manager,
            world_name=world_name,
            model_name=environ.get("MODEL_NAME"),
            landscape=environ.get("LANDSCAPE_DESCRIPTION"),
            animals_active=environ.get("ANIMALS_ACTIVE", "True").lower() == "true",
        )

        # User transcript management
        self.user_transcripts = {}

        # Set up user input processor
        self.user_input_processor: UserInputProcessor = UserInputProcessor(
            self.world_manager
        )

    # This is async so cannot be in the constructor
    async def start_orchestrating(self) -> None:
        # Ready to Start consuming messages
        await self.mbh.set_up_nats()

    # Perform cleanup here (e.g., closing file handles)
    def clean_up(self) -> None:
        # Close all user transcript files
        for user_name, f in self.user_transcripts.items():
            f.close()
            logger.info(f"Closed transcript file for {user_name}")


async def main() -> None:
    # Get world name from command line or environment variable
    world_name: str
    if len(argv) > 1:
        world_name = argv[1]
    else:
        world_name = environ.get("ORCHESTRATOR_WORLD_NAME", "corvid")

    # Create and start the orchestrator
    orchestrator: Orchestrator = Orchestrator(world_name)
    try:
        await orchestrator.start_orchestrating()
        await asyncio.Event().wait()  # Keeps the event loop running
    except ShutdownException as e:
        logger.critical(f"Shutdown initiated: {e}")
        orchestrator.clean_up()
        logger.info("Cleanup complete. Exiting.")


if __name__ == "__main__":
    asyncio.run(main())
