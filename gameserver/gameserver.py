import socket
import socketio
import eventlet
from gameutils import log, create_folder_if_not_exists, make_name_safe_for_files
from player import Player
from game_manager import GameManager

log("Setting up SocketIO")
sio = socketio.Server(cors_allowed_origins="*")
app = socketio.WSGIApp(sio)


# Event handlers
# These use global game_server


@sio.event
def connect(sid, environ):
    log("Client connected:", sid)


# Handle disconnects
@sio.event
def disconnect(sid):
    log("Client disconnected:", sid)
    # TODO: allow players to reconnect (for now disconnect is same as quit)
    game_server.remove_player(
        sid, "You have been logged out as your client disconnected."
    )


@sio.event
def user_action(sid, player_input):
    if sid in game_server.players:
        player = game_server.players[sid]
        log(f"Received user action: {player_input} from {sid}")
        player_response = player.process_player_input(player_input)
        # Respond to player
        if player_response:
            sio.emit("game_update", player_response, sid)
    else:
        log(f"Received user action from non-existent player {sid}")
        sio.emit(
            "logout",
            "You have been logged out due to a server error. Please log in again.",
            sid,
        )


@sio.event
def set_player_name(sid, player_name):
    log(f"Received user name: {player_name} from {sid}")

    # Strip out any whitespace (defensive in case of client bug)
    player_name = player_name.strip()

    # Set up new game
    if not (
        player_name
        and len(player_name) <= 20
        and player_name.isprintable()
        and make_name_safe_for_files(player_name) == player_name
    ):
        # Issue with player name setting
        sio.emit(
            "logout",
            "Sorry, that name is not valid. Please try again.",
            sid,
        )
    elif not game_server.player_name_is_unique(player_name):
        # Issue with player name setting
        sio.emit("game_update", "Sorry, that name is already taken.", sid)
        # Player logging out or trying an existing name is the same thing for now
        sio.emit(
            "logout",
            "Sorry, that name is already taken.",
            sid,
        )
    else:
        player = Player(game_server, sid, player_name)
        # Spawn the world-wide metadata loop when the first player enters the game.
        # This is to minimise resource usage when no one is playing.
        game_server.activate_background_loop()


# End of event handlers


if __name__ == "__main__":
    hostname = socket.getfqdn()
    if hostname.endswith(".lan"):
        hostname = hostname[:-4]
    log(f"Starting up game server on {hostname}")
    game_server = GameManager(sio)
    eventlet.wsgi.server(eventlet.listen(("0.0.0.0", 3001)), app)
