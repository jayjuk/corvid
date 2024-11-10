from logger import setup_logger, exit
from typing import List, Dict, Optional
import eventlet
import socketio
import time
from os import environ
import re
from aimanager import AIManager
from utils import get_critical_env_variable

# Set up logger
logger = setup_logger("airequester")

# Register the client with the server
sio = socketio.Client()


# Class to manage the AI's interaction with the game server
class AIRequester:

    def __init__(
        self,
        model_name: str,
        system_message: str,
    ) -> None:
        # Constructor
        self.model_name = model_name
        self.system_message = system_message
        # Set up the AI manager
        self.ai_manager = AIManager(
            model_name=model_name,
            system_message=system_message,
        )

    def submit_request(self, prompt: str, system_message: str = "") -> str:
        this_system_message: str = (
            system_message if system_message else self.system_message
        )
        logger.info(
            f"Submitting request: {prompt} with system message: {this_system_message}"
        )
        return self.ai_manager.submit_request(
            request=prompt, system_message=this_system_message
        )

    def work_loop(self):
        while True:
            # Just wait for events for now
            eventlet.sleep(60)


# Non-class functions below here (SocketIO event handlers etc.)


# Connect to SocketIO server, trying again if it fails
def connect_to_server(hostname: str) -> None:
    connected: bool = False
    max_wait: int = 240  # 4 minutes
    wait_time: int = 4
    while not connected and wait_time <= max_wait:
        try:
            sio.connect(hostname)
            connected = True
        except Exception as e:
            logger.info(
                f"Could not connect to server. Retrying in {wait_time} seconds..."
            )
            eventlet.sleep(wait_time)
            wait_time = int(wait_time * 2)

    if not connected:
        exit(logger, "Could not connect to Game Server. Is it running?")


# SocketIO event handlers


# Game update event handler
@sio.on("ai_request")
def catch_all(data: Dict) -> None:
    logger.info(f"Received AI request: {data}")
    if data:
        if "prompt" not in data:
            exit(logger, "Received invalid AI request")
        # Submit the request to the AI
        ai_response = ai_requester.submit_request(
            prompt=data["prompt"],
            system_message=data.get(
                "system_message", "You are a helpful AI assistant for a game server."
            ),
        )
        if ai_response:
            response_package = {
                "ai_response": ai_response,
                "request_id": data["request_id"],
            }
            # Emit event back to server
            sio.emit(
                "ai_response",
                response_package,
            )
        else:
            exit(logger, "AI request returned no response")

    else:
        exit(logger, "Received invalid event")


# Shutdown event handler
@sio.on("shutdown")
def catch_all(data: Dict) -> None:
    logger.info(f"Shutdown event received: {data}. Exiting immediately.")
    ai_requester.time_to_die = True
    sio.disconnect()
    sio.eio.disconnect()
    exit(logger, "AI requester shutting down.")


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


# Connect to SocketIO server, trying again if it fails
def connect_to_server(hostname: str) -> None:
    connected: bool = False
    max_wait: int = 240  # 4 minutes
    wait_time: int = 4
    while not connected and wait_time <= max_wait:
        try:
            sio.connect(hostname)
            connected = True
        except Exception as e:
            logger.info(
                f"Could not connect to server. Retrying in {wait_time} seconds..."
            )
            eventlet.sleep(wait_time)
            wait_time = int(wait_time * 2)

    if not connected:
        exit(logger, "Could not connect to Game Server. Is it running?")


# Main function to start the program
if __name__ == "__main__":
    # Change log file name to include AI name
    logger = setup_logger("ai_requester.log")

    # Set hostname (default is "localhost" to support local pre container testing)
    # hostname = socket.getfqdn()
    # if hostname.endswith(".lan"):
    #     hostname = hostname[:-4]
    hostname: str = environ.get("GAMESERVER_HOSTNAME") or "localhost"
    # TODO #65 Do not allow default port, and make this common
    port: str = environ.get("GAMESERVER_PORT", "3001")
    logger.info(f"Starting up AI requester hostname {hostname}")
    # Connect to the server. If can't connect, warn user that the Game Server may not be running.
    try:
        connect_to_server(f"http://{hostname}:{port}")
    except Exception as e:
        exit(logger, f"Could not connect to server: {e}\nIs the Game Server running?")
    logger.info("Connected to server.")
    # Create AI Worker
    ai_requester = AIRequester(
        model_name=get_critical_env_variable("MODEL_NAME"),
        system_message=environ.get("MODEL_SYSTEM_MESSAGE"),
    )

    # Check for outstanding requests
    sio.emit("missing_ai_request", {})

    # This is where the main processing of inputs happens
    eventlet.spawn(ai_requester.work_loop())

    # This keeps the SocketIO event processing going
    sio.wait()
