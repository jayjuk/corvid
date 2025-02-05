# Set up logger first
from utils import setup_logger, exit, get_logs_folder, connect_to_server
from typing import Dict, Optional, Any, Callable, Tuple
from os import environ
from sys import argv
import time
from os import path, makedirs
import socketio

# Set up logger before importing other own modules
logger = setup_logger("Game Server", sio=None)

from azurestoragemanager import AzureStorageManager
from gamemanager import GameManager
from player import Player
from player_input_processor import PlayerInputProcessor
from messagebroker_helper import MessageBrokerHelper

# Register the client with the server
sio = socketio.Client()

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


# Player setup
def set_player_name(data: Dict[str, str]) -> None:
    sid: str = data["sid"]
    player_info: Dict[str, str] = data["player_info"]
    logger.info(
        f"Client requesting player setup: {sid}, {player_info.get('name')}, {player_info.get('role')}"
    )
    outcome: Optional[str] = game_manager.process_player_setup(
        sid, player_info, player_input_processor.get_help_text()
    )
    # Blank outcome = success
    if outcome:
        # Issue with player name setting - indicate using name_invalid event, with error message
        sio.emit(
            "name_invalid",
            outcome,
            sid,
        )
    else:
        create_player_transcript(player_info.get("name"))


# User action
def user_action(data: Dict[str, str]):
    sid: str = data["sid"]
    player_input: str = data["player_input"]

    if sid in game_manager.players:
        player: Player = game_manager.players[sid]
        logger.info(f"Received user action: {player_input} from {sid} ({player.name})")
        sio.emit("game_update", f"You: {player_input}", sid)
        command_function: Callable
        command_args: Tuple
        response_to_player: Optional[str]

        # Process player input to resolve the command and arguments, or return an error message
        command_function, command_args, response_to_player = (
            player_input_processor.process_player_input(player, player_input)
        )
        if command_function:
            logger.info(
                f"Command function: {command_function.__name__}, Args: {command_args}"
            )
            response_to_player = command_function(*command_args)

        # Respond to player
        if response_to_player:
            player.add_input_history(f"Game: {response_to_player}")
            sio.emit("game_update", response_to_player, sid)

        # Log player input and response
        log_to_player_transcript(player.name, player_input, response_to_player)
    else:
        logger.info(f"Received user action from non-existent player {sid}")
        sio.emit(
            "logout",
            "You have been logged out due to a server error. Please log in again.",
            sid,
        )


# Disconnection
def user_disconnect(data: Dict[str, str]) -> None:
    sid: str = data["sid"]
    logger.info(f"Client disconnected: {sid}")
    # TODO #72 Allow players to reconnect (for now disconnect is same as quit)
    game_manager.remove_player(
        sid, "You have been logged out as your client disconnected."
    )


game_manager: GameManager


# process_missing_image_request
def missing_image_request(data: Dict) -> None:
    logger.info("Received missing images request")
    game_manager.process_missing_image_request()


def image_creation_response(data: Dict) -> None:
    logger.info(f"Received image creation response: {data}")
    game_manager.process_image_creation_response(
        data["room_name"], data["image_filename"], data["success"]
    )


def missing_ai_request(data: Dict) -> None:
    logger.info("Received request for missing AI requests ")
    game_manager.ai_manager.process_missing_ai_request()


def missing_summon_player_request(data: Dict) -> None:
    logger.info("Received request for missing Summon Player requests ")
    game_manager.process_missing_summon_player_request()


def summon_player_response(data: Dict) -> None:
    logger.info(f"Received summon player response: {data}")
    game_manager.process_summon_player_response(data["request_id"])


def ai_response(data: Dict) -> None:
    logger.info(f"Received AI response: {data}")
    if (
        "request_id" in data
        and data["request_id"] in game_manager.ai_manager.remote_requests
    ):
        # TODO #98 should game server be allowed to access ai manager directly?
        player: Player
        response_to_player: str
        player, response_to_player = game_manager.ai_manager.process_ai_response(data)
        print(f"ai_response: Response to player: {response_to_player}")
        from pprint import pprint

        pprint(response_to_player)
        if response_to_player:
            player.add_input_history(f"Game: {response_to_player}")
            sio.emit("game_update", response_to_player, player.sid)
            logger.info(
                f"Emitting this response from the handler of this response: {response_to_player}"
            )

        # Log player input and response
        log_to_player_transcript(player.name, "[AI response]", response_to_player)

    else:
        exit(logger, f"Valid request ID not found: data {data}")


# End of event handlers


if __name__ == "__main__":
    # Instantiate the message broker helper
    def message_broker_callback(message: str) -> None:
        logger.info(f"Received message: {message}")

    # Set up the message broker
    logger.info("Setting up message broker")
    mbh = MessageBrokerHelper(
        environ.get("GAMESERVER_HOSTNAME", "localhost"),
        {
            # Image creation
            "missing_image_request": {
                "mode": "subscribe",
                "callback": missing_image_request,
            },
            "image_creation_request": {"mode": "publish"},
            "image_creation_response": {
                "mode": "subscribe",
                "callback": image_creation_response,
            },
            # General AI requests
            "missing_ai_request": {"mode": "subscribe", "callback": missing_ai_request},
            "ai_request": {"mode": "publish"},
            "ai_response": {"mode": "subscribe", "callback": ai_response},
            # Summon player
            "missing_summon_player_request": {
                "mode": "subscribe",
                "callback": missing_summon_player_request,
            },
            "summon_player_request": {"mode": "publish"},
            "summon_player_response": {
                "mode": "subscribe",
                "callback": summon_player_response,
            },
            "user_disconnect": {"mode": "subscribe", "callback": user_disconnect},
            "set_player_name": {"mode": "subscribe", "callback": set_player_name},
            "user_action": {"mode": "subscribe", "callback": user_action},
        },
        use_threading=True,
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
    )
    player_input_processor: PlayerInputProcessor = PlayerInputProcessor(game_manager)

    # Connect to the server. If can't connect, warn user that the Game Server may not be running.
    connect_to_server(logger, sio)

    # Start the Socket.IO client
    sio.wait()
