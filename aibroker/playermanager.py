import eventlet

eventlet.monkey_patch()

from typing import Dict
import os
from utils import (
    get_critical_env_variable,
    setup_logger,
    exit,
    get_logs_folder,
    connect_to_server,
)
import subprocess
import json
import time
import socketio


# Class to manage the AI's interaction with the game server
class PlayerManager:

    def __init__(
        self,
        init_filename: str,
    ) -> None:
        # Constructor

        # Read the player data from the file
        self.player_data: Dict = self.read_player_data(init_filename)

        player_count = 0

        for player in self.player_data["players"]:
            player_count += 1
            # Add the team briefing to the player data
            player["team_briefing"] = self.player_data["team_briefing"]
            print(f"Creating player {player_count}")
            self.create_player(player)  # Create the player

    # Check file is JSON and parse it into a dictionary
    def read_player_data(self, filename: str) -> Dict:
        try:
            with open(filename, "r") as f:
                player_data = json.load(f)
        except FileNotFoundError:
            exit(logger, f"File not found: {filename}")
        except json.JSONDecodeError:
            exit(logger, f"File is not valid JSON: {filename}")
        return player_data

    # Create a player
    def create_player(self, player_dict: Dict) -> None:
        # Create a player
        logger.info(f"Creating player: {player_dict}")

        env_vars = {
            "MODEL_NAME": player_dict.get(
                "model_name", get_critical_env_variable("MODEL_NAME")
            ),
            "AI_NAME": player_dict.get("player_name", ""),
            "AI_MODE": "player",
            "AI_COUNT": "1",
            "MODEL_SYSTEM_MESSAGE": player_dict.get("team_briefing", "")
            + " "
            + player_dict.get("player_briefing", ""),
        }

        def run_player_process(env_vars):

            print("**************** Running player process")

            env = {**os.environ, **env_vars}
            # Generate unique log file name based on timestamp
            seconds_since_epoch = str(time.time())

            log_file_name = os.path.join(
                get_logs_folder(),
                f"player_{env_vars['AI_NAME']}_{seconds_since_epoch}.log",
            )
            logger.info(f"Log file name: {log_file_name}")
            with open(log_file_name, "w") as f:
                subprocess.Popen(
                    ["python", "aibroker.py"],
                    env=env,
                    stdout=f,
                    stderr=f,
                )

        # Run the player process in a background thread

        # TODO #100 Improve solution for managing AI processes
        eventlet.spawn(run_player_process, env_vars)
        logger.info(f"Player created: {env_vars}")


# Register the client with the server
sio = socketio.Client()

# SocketIO event handlers


# Game update event handler
@sio.on("summon_player_request")
def catch_all(data: Dict) -> None:
    logger.info(f"Received Summon Player request: {data}")
    if "request_data" in data and "request_id" in data:
        # If data["request_data"] is a string, expect that to just be the player briefing
        if isinstance(data["request_data"], str):
            logger.info(
                f"Assuming request is just a player briefing: {data['request_data']}"
            )
            data["request_data"] = {"player_briefing": data["request_data"]}
        player_manager.create_player(data["request_data"])
        sio.emit("summon_player_response", {"request_id": data["request_id"]})
    else:
        exit(logger, f"Invalid request data: {data}")


# Shutdown event handler
@sio.on("shutdown")
def catch_all(data: Dict) -> None:
    logger.info(f"Shutdown event received: {data}. Shutting down immediately.")
    player_manager.time_to_die = True
    sio.disconnect()
    sio.eio.disconnect()
    exit(logger, "All done.")


# SocketIO connection handlers


# Connection event handler
@sio.event
def connect() -> None:
    logger.info("Connected to Server.")


# Connection error event handler
@sio.event
def connect_error(data: Dict) -> None:
    logger.error(data)


# Disconnection event handler
@sio.event
def disconnect() -> None:
    # TODO #95 Handle reconnection e.g. when Game Server restarts
    logger.info("Disconnected from Server.")


# Main

# Set up logger
logger = setup_logger("Player Manager", sio=sio)

connect_to_server(logger, sio)

# Create AI Worker
player_manager = PlayerManager(
    init_filename=get_critical_env_variable("AI_PLAYER_FILE_NAME"),
)

# Check for outstanding requests
sio.emit("missing_summon_player_request", {})
logger.info("Ready...")

# This keeps the SocketIO event processing going
sio.wait()
