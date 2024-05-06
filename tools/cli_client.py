from logger import setup_logger, exit
from typing import List, Dict
import eventlet
import socketio
import time
from os import environ
import re
from urllib3.exceptions import HTTPError

# Set up logger
logger = setup_logger("cliclient")

# Register the client with the server
sio = socketio.Client()


# Class to manage the AI's interaction with the game server
class CliClient:
    def __init__(self):
        # Constructor
        self.time_to_die: bool = False
        self.player_name: str = "TBD"
        self.input_token_count: int = 0
        self.output_token_count: int = 0

        self.set_player_name()

    # The main processing loop
    def response_loop(self) -> None:
        while True:
            # Exit own thread when time comes
            if self.time_to_die:
                return

            self.poll_event_log()
            # Record time
            self.last_time = time.time()

    # Get AI name from the LLM using the AI manager
    def set_player_name(self) -> str:

        request = "What do you want your name to be in this game?"

        player_name = None
        while not player_name or " " in player_name:
            # Keep trying til they get the name right
            player_name = input(request).strip(".")
        self.player_name = player_name
        return player_name

    # Log the game events for the AI to process
    def output_event(self, event_text: str) -> None:
        print(event_text)

    # Submit the game's updates as input to the AI manager
    def submit_input(self) -> str:
        command_text = "Please enter a single valid command phrase:"
        return input(command_text)

    # Check the event log for new events to process
    def poll_event_log(self) -> None:
        response = self.submit_input()
        # Check again we are still running (due to wait on model)
        if self.time_to_die:
            return
        if response:
            # Submit AI's response to the game server
            sio.emit("user_action", response)
            # If response was to exit, exit here (after sending the exit message to the game server)
            if response == "exit":
                exit(logger, "You have exited the game.")
        else:
            exit(logger, "You returned empty response")


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
@sio.on("game_update")
def catch_all(data: Dict) -> None:
    if data:
        logger.info(f"Received game update event: {data}")
        cli_client.output_event(data)
    else:
        exit(logger, "Received empty game update event")


# Instructions event handler
@sio.on("instructions")
def catch_all(data: Dict) -> None:
    cli_client.output_event(data)


# Shutdown event handler
@sio.on("shutdown")
def catch_all(data: Dict) -> None:
    logger.info(f"Shutdown event received: {data}. Exiting immediately.")
    cli_client.time_to_die = True
    sio.disconnect()
    sio.eio.disconnect()
    exit(logger, "Shutting down.")


# This might happen if the AI quits!
@sio.on("logout")
def catch_all(data: Dict) -> None:
    logger.info(f"Logout event received: {data} did you quit?")
    sio.disconnect()
    exit(logger, "Logout received.")


# Room update event handler
@sio.on("room_update")
def catch_all(data: Dict) -> None:
    # For now nothing, do not even log - this consists of the room description, and the image URL, not relevant to AI
    print("ROOM UPDATE:", data)


# Player update event handler
@sio.on("game_data_update")
def catch_all(data: Dict) -> None:
    pass  # print("GAME UPDATE:", data)


# Catch all other events
@sio.on("*")
def catch_all(event, data: Dict) -> None:
    logger.warn(f"Received other unexpected event '{event}': {data}")


# SocketIO connection handlers


# Connection event handler
@sio.event
def connect() -> None:
    logger.info("Connected to Server.")
    # Emit the AI's chosen name to the server
    sio.emit("set_player_name", {"name": cli_client.player_name, "role": "player"})


# Invalid name, try again
@sio.on("name_invalid")
def catch_all(data: Dict) -> None:
    logger.info(f"Invalid name event received: {data}")
    cli_client.set_player_name(data)
    sio.emit("set_player_name", {"name": cli_client.player_name, "role": "player"})


# Connection error event handler
@sio.event
def connect_error(data: Dict) -> None:
    logger.error(data)
    # exit(logger, "Connection failure!")


# Disconnection event handler
@sio.event
def disconnect() -> None:
    logger.info("Disconnected from Server.")


# Main function to start the AI Broker
if __name__ == "__main__":
    # Set up logging to file and console
    logger.info("Starting up CLI Client")

    cli_client = CliClient()

    hostname: str = environ.get("GAMESERVER_HOSTNAME") or "localhost"
    port: str = environ.get("GAMESERVER_PORT", "3001")
    # Connect to the server. If can't connect, warn user that the Game Server may not be running.
    try:
        connect_to_server(f"http://{hostname}:{port}")
    except Exception as e:
        exit(logger, f"Could not connect to server: {e}\nIs the Game Server running?")
    logger.info("Connected to server.")
    # This is where the main processing of inputs happens
    eventlet.spawn(cli_client.response_loop())

    # This keeps the SocketIO event processing going
    sio.wait()
