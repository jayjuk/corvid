# Set up logger first
from logger import setup_logger
from typing import Dict, Optional, Any, Callable, Tuple
from os import environ
from sys import argv
import time
from os import path, makedirs

logger = setup_logger("gameserver")

import socket
import socketio
import eventlet
from azurestoragemanager import AzureStorageManager
from gamemanager import GameManager
from player import Player
from player_input_processor import PlayerInputProcessor

# This is the main game server file. It sets up the SocketIO server and handles events only

logger.info("Setting up SocketIO")
sio = socketio.Server(cors_allowed_origins="*")
app = socketio.WSGIApp(sio)

# Transcript management


# Create a log file for model responses
def get_player_transcript_file_name(player_name: str) -> str:
    logs_folder: str = "logs"
    makedirs(logs_folder, exist_ok=True)
    return path.join(logs_folder, f"{player_name}_game_transcript.txt")


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


# Event handlers


# Connection
@sio.event
def connect(sid: str, environ: Dict[str, Any]) -> None:
    logger.info(f"Client connected: {sid}")


# Player setup
@sio.event
def set_player_name(sid: str, player_info: Dict[str, str]) -> None:
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


# Player input from the client
@sio.event
def user_action(sid: str, player_input: str):
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
@sio.event
def disconnect(sid: str) -> None:
    logger.info(f"Client disconnected: {sid}")
    # TODO #72 Allow players to reconnect (for now disconnect is same as quit)
    game_manager.remove_player(
        sid, "You have been logged out as your client disconnected."
    )


# End of event handlers


if __name__ == "__main__":
    hostname: str = socket.getfqdn()
    if hostname.endswith(".lan"):
        hostname = hostname[:-4]
    # TODO #65 Do not allow default port, and make this common
    port: int = int(environ.get("GAMESERVER_PORT", "3001"))

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
        storage_manager,
        world_name=world_name,
        model_name=environ.get("MODEL_NAME"),
        image_model_name=environ.get("IMAGE_MODEL_NAME"),
    )
    player_input_processor: PlayerInputProcessor = PlayerInputProcessor(game_manager)
    logger.info(f"Launching WSGI server on {hostname}:{port}")
    eventlet.wsgi.server(eventlet.listen(("0.0.0.0", port)), app)
