# Set up logger first
from logger import setup_logger
from typing import Dict, Optional, Any, Callable, Tuple
from os import environ

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


# Event handlers


# Connection
@sio.event
def connect(sid: str, environ: Dict[str, Any]) -> None:
    logger.info(f"Client connected: {sid}")


# Player setup
@sio.event
def set_player_name(sid: str, player: Player) -> None:
    logger.info(
        f"Client requesting player setup: {sid}, {player.get('name')}, {player.get('role')}"
    )
    outcome: Optional[str] = game_manager.process_player_setup(
        sid, player, player_input_processor.get_help_text()
    )
    # Blank outcome = success
    if outcome:
        # Issue with player name setting - log out client with error message
        sio.emit(
            "logout",
            outcome,
            sid,
        )


# Player input from the client
@sio.event
def user_action(sid: str, player_input: str):
    if sid in game_manager.players:
        player: Player = game_manager.players[sid]
        logger.info(f"Received user action: {player_input} from {sid} ({player.name})")
        sio.emit("game_update", f"You: {player_input}", sid)
        command_function: Callable
        command_args: Tuple
        player_response: Optional[str]

        # Process player input to resolve the command and arguments, or return an error message
        command_function, command_args, player_response = (
            player_input_processor.process_player_input(player, player_input)
        )
        if command_function:
            logger.info(
                f"Command function: {command_function.__name__}, Args: {command_args}"
            )
            player_response = command_function(*command_args)

        # Respond to player
        if player_response:
            player.add_input_history(f"Game: {player_response}")
            sio.emit("game_update", player_response, sid)
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
    world_name: str = environ.get("GAMESERVER_WORLD_NAME", "jaysgame")
    logger.info(f"Starting up game manager - world '{world_name}'")
    storage_manager: AzureStorageManager = AzureStorageManager()
    game_manager: GameManager = GameManager(sio, storage_manager, world_name=world_name)
    player_input_processor: PlayerInputProcessor = PlayerInputProcessor(game_manager)
    logger.info(f"Launching WSGI server on {hostname}:{port}")
    eventlet.wsgi.server(eventlet.listen(("0.0.0.0", port)), app)
