from gamemanager import GameManager
from storagemanager import StorageManager
from player import Player
from player_input_processor import PlayerInputProcessor
import eventlet
import time
import asyncio
from os import environ

# import socket
import socketio

sio = socketio.Server(cors_allowed_origins="*")
app = socketio.WSGIApp(sio)


print("*** Setting up ***")
storage_manager = StorageManager()
game_manager = GameManager(
    sio=sio,
    storage_manager=storage_manager,
    world_name="remotetest",
)
player = Player(game_manager.world, 0, "TestPlayer")

port: int = int(environ.get("GAMESERVER_PORT", "3001"))

eventlet.wsgi.server(eventlet.listen(("0.0.0.0", port)), app)

time.sleep(10)

print("Submitting remote request")
await game_manager.ai_manager.submit_remote_request(
    player, "ai_request", "test prompt", "you are testing a remote request"
)


# sleep forever
while True:
    time.sleep(1)
