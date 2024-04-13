import eventlet
import socketio
import sys
from os import environ

# Register the client with the server
sio = socketio.Client()

if __name__ == "__main__":
    # Set hostname (default is "localhost" to support local pre container testing)
    # hostname = socket.getfqdn()
    # if hostname.endswith(".lan"):
    #     hostname = hostname[:-4]
    hostname = environ.get("GAMESERVER_HOSTNAME") or "localhost"
    port = environ.get("GAMESERVER_PORT", "3001")
    sio.connect(f"http://{hostname}:{port}")
    sio.emit("set_player_name", {"name": "system", "role": "player"})
    eventlet.sleep(1)
    sio.emit("user_action", "xox")
    eventlet.sleep(1)
