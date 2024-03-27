# Set up logger first
from logger import setup_logger

logger = setup_logger("gameserver")

import socket
import socketio
import eventlet
from azurestoragemanager import AzureStorageManager
from gamemanager import GameManager
from os import environ

# This is the main game server file. It sets up the SocketIO server and handles events only

logger.info("Setting up SocketIO")
sio = socketio.Server(cors_allowed_origins="*")
app = socketio.WSGIApp(sio)


# Event handlers


# Connection
@sio.event
def connect(sid, environ):
    logger.info(f"Client connected: {sid}")


# Player setup
@sio.event
def set_player_name(sid, player):
    logger.info(
        f"Client requesting player setup: {sid}, {player.get('name')}, {player.get('role')}"
    )
    outcome = game_manager.process_player_setup(sid, player)
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
def user_action(sid, player_input):
    if sid in game_manager.players:
        player = game_manager.players[sid]
        logger.info(f"Received user action: {player_input} from {sid} ({player.name})")
        player.add_input_history(f"You: {player_input}")
        sio.emit("game_update", f"You: {player_input}", sid)
        player_response = game_manager.process_player_input(player, player_input)
        # Respond to player
        if player_response:
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
def disconnect(sid):
    logger.info(f"Client disconnected: {sid}")
    # TODO #72 Allow players to reconnect (for now disconnect is same as quit)
    game_manager.remove_player(
        sid, "You have been logged out as your client disconnected."
    )


# End of event handlers


if __name__ == "__main__":
    hostname = socket.getfqdn()
    if hostname.endswith(".lan"):
        hostname = hostname[:-4]
    # TODO #65 Do not allow default port, and make this common
    port = int(environ.get("GAMESERVER_PORT", "3001"))
    world_name = environ.get("GAMESERVER_WORLD_NAME", "jaysgame")
    logger.info(f"Starting up game manager - world '{world_name}'")
    storage_manager = AzureStorageManager()
    game_manager = GameManager(sio, storage_manager, world_name=world_name)
    logger.info(f"Launching WSGI server on {hostname}:{port}")
    eventlet.wsgi.server(eventlet.listen(("0.0.0.0", port)), app)
