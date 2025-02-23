# Set up logger first
from utils import set_up_logger, exit, get_logs_folder
from typing import Dict, Optional, Any, Callable, Tuple
from os import environ
from sys import argv
import time
from os import path, makedirs
import asyncio

# Set up logger before importing other own modules
logger = set_up_logger("Game Server")

from azurestoragemanager import AzureStorageManager
from gamemanager import GameManager
from player import Player
from player_input_processor import PlayerInputProcessor
from messagebroker_helper import MessageBrokerHelper

# Register the client with the server
sio = None  # socketio.Client()

# Transcript management


# Create a log file for model responses
def get_player_transcript_file_name(player_name: str) -> str:
    makedirs(get_logs_folder(), exist_ok=True)
    return path.join(get_logs_folder(), f"{player_name}_game_transcript.txt")


def create_player_transcript(player_name: str) -> None:
    with open(get_player_transcript_file_name(player_name), "w") as f:
        f.write(f"# Player input and response log for {player_name}\n\n")


# Log model response to file
def log_to_player_transcript(
    player_name: str, request: str = "", response: str = ""
) -> None:
    with open(get_player_transcript_file_name(player_name), "a") as f:
        timestamp: str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        f.write(f"{timestamp} {player_name}: {request}\n")
        f.write(f"{timestamp} Game: {response}\n\n")


async def main() -> None:

    # Event handlers

    # Player setup
    async def set_player_name(player_info: Dict[str, str]) -> None:
        player_id: str = player_info["player_id"]
        logger.info(
            f"Client requesting player setup: {player_id}, {player_info.get('name')}, {player_info.get('role')}"
        )
        outcome: Optional[str] = await game_manager.process_player_setup(
            player_id, player_info, player_input_processor.get_help_text()
        )
        # Blank outcome = success
        if outcome:
            # Issue with player name setting - indicate using name_invalid event, with error message
            await mbh.publish(
                "name_invalid",
                outcome,
                player_id,
            )
        else:
            create_player_transcript(player_info.get("name"))

    # User action
    async def player_action(data: Dict[str, str]):
        player_id: str = data["player_id"]
        player_input: str = data["player_input"]

        if player_id in game_manager.players:
            player: Player = game_manager.players[player_id]
            logger.info(
                f"Received user action: {player_input} from {player_id} ({player.name})"
            )
            await mbh.publish("game_update", f"You: {player_input}", player_id)
            command_function: Callable
            command_args: Tuple
            response_to_player: Optional[str]

            # Process player input to resolve the command and arguments, or return an error message
            result = await player_input_processor.process_player_input(
                player, player_input
            )
            (command_function, command_args, response_to_player) = result
            if command_function:
                if isinstance(command_function, Callable):
                    logger.info(
                        f"Command function: {command_function.__name__}, Args: {command_args}"
                    )
                    if asyncio.iscoroutinefunction(command_function):
                        response_to_player = await command_function(*command_args)
                    else:
                        response_to_player = command_function(*command_args)
                else:
                    exit(
                        logger,
                        f"Command function not found for input: {player_input}, command_function = {command_function}",
                    )

            # Respond to player
            if response_to_player:
                player.add_input_history(f"Game: {response_to_player}")
                await mbh.publish("game_update", response_to_player, player_id)

            # Log player input and response
            log_to_player_transcript(player.name, player_input, response_to_player)
        else:
            logger.info(f"Received user action from non-existent player {player_id}")
            await mbh.publish(
                "logout",
                "You have been logged out due to a server error. Please log in again.",
                player_id,
            )

    # Disconnection
    def user_disconnect(data: Dict[str, str]) -> None:
        player_id: str = data["player_id"]
        logger.info(f"Client disconnected: {player_id}")
        # TODO #72 Allow players to reconnect (for now disconnect is same as quit)
        game_manager.remove_player(
            player_id, "You have been logged out as your client disconnected."
        )

    async def image_creation_response(data: Dict) -> None:
        logger.info(f"Received image creation response: {data}")
        await game_manager.process_image_creation_response(
            data["room_name"], data["image_filename"], data["success"]
        )

    async def summon_player_response(data: Dict) -> None:
        logger.info(f"Received summon player response: {data}")
        game_manager.process_summon_player_response(data["request_id"])

    async def ai_response(data: Dict) -> None:
        logger.info(f"Received AI response: {data}")
        if (
            "request_id" in data
            and data["request_id"] in game_manager.ai_manager.remote_requests
        ):
            # TODO #98 should game server be allowed to access ai manager directly?
            player: Player
            response_to_player: str
            (player, response_to_player) = (
                await game_manager.ai_manager.process_ai_response(data)
            )
            if response_to_player:
                player.add_input_history(f"Game: {response_to_player}")
                await mbh.publish("game_update", response_to_player, player.player_id)
                logger.info(
                    f"Emitting this response from the handler of this response: {response_to_player}"
                )

            # Log player input and response
            log_to_player_transcript(player.name, "[AI response]", response_to_player)

        else:
            exit(logger, f"Valid request ID not found: data {data}")

    # End of event handlers

    # Set up the message broker
    logger.info("Setting up message broker")
    mbh = MessageBrokerHelper(
        environ.get("GAMESERVER_HOSTNAME", "localhost"),
        {
            # Client messages
            "instructions": {"mode": "publish"},
            "name_invalid": {"mode": "publish"},
            "room_update": {"mode": "publish"},
            "game_update": {"mode": "publish"},
            "game_data_update": {"mode": "publish"},
            "logout": {"mode": "publish"},
            # Image creation
            "image_creation_request": {"mode": "publish"},
            "image_creation_response": {
                "mode": "subscribe",
                "callback": image_creation_response,
            },
            # General AI requests
            "ai_request": {"mode": "publish"},
            "ai_response": {"mode": "subscribe", "callback": ai_response},
            # Summon player
            "summon_player_request": {"mode": "publish"},
            "summon_player_response": {
                "mode": "subscribe",
                "callback": summon_player_response,
            },
            "user_disconnect": {"mode": "subscribe", "callback": user_disconnect},
            "set_player_name": {"mode": "subscribe", "callback": set_player_name},
            "player_action": {"mode": "subscribe", "callback": player_action},
        },
    )
    logger.info("Message broker set up")

    # Get world name from command line or environment variable
    world_name: str
    if len(argv) > 1:
        world_name = argv[1]
    else:
        world_name = environ.get("GAMESERVER_WORLD_NAME", "jaysgame")

    logger.info(f"Starting up game manager - world '{world_name}'")
    storage_manager: AzureStorageManager = AzureStorageManager()
    game_manager: GameManager = GameManager(
        sio,
        mbh,
        storage_manager,
        world_name=world_name,
        model_name=environ.get("MODEL_NAME"),
        landscape=environ.get("LANDSCAPE_DESCRIPTION"),
        animals_active=environ.get("ANIMALS_ACTIVE", "True").lower() == "true",
    )
    player_input_processor: PlayerInputProcessor = PlayerInputProcessor(game_manager)

    # Start consuming messages
    await mbh.set_up_nats()

    await asyncio.Event().wait()  # Keeps the event loop running


if __name__ == "__main__":
    asyncio.run(main())
