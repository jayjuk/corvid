from logger import setup_logger, exit
from typing import List, Dict, Optional
import eventlet
import socketio
import time
from os import environ
import re
from urllib3.exceptions import HTTPError
from aimanager import AIManager

# Set up logger
logger = setup_logger("aibroker")

# Register the client with the server
sio = socketio.Client()


# Class to manage the AI's interaction with the game server
class AIBroker:
    def __init__(self, mode: str = "player", model_name: str = None):
        # Constructor
        self.mode: Optional[str] = mode
        self.time_to_die: bool = False
        self.game_instructions: str = ""
        self.event_log: List[str] = []
        self.max_history: int = 50
        self.max_wait: int = 5  # secs
        self.last_time: float = time.time()
        self.active: bool = True
        self.player_name: str = "TBD"
        self.input_token_count: int = 0
        self.output_token_count: int = 0

        # Set up the AI manager
        self.ai_manager = AIManager(
            system_message=self.get_ai_instructions(), model_name=model_name
        )

        # Get the AI's name
        # TODO #89 Enable many AI players to be managed by the same broker
        self.set_ai_name()

    # The main processing loop
    def ai_response_loop(self) -> None:
        while True:
            # Exit own thread when time comes
            if self.time_to_die:
                return

            # Check if we need to wait before polling the event log
            wait_time = self.max_wait - (time.time() - self.last_time)
            if wait_time > 0:
                # don't do anything for now
                eventlet.sleep(wait_time)
            self.poll_event_log()
            # Record time
            self.last_time = time.time()

    # AI manager will record instructions from the game server
    # Which are given to each player at the start of the game
    def record_instructions(self, data: str) -> None:
        self.game_instructions += data + "\n"
        self.ai_manager.set_system_message(self.game_instructions)

    # AI manager will get instructions from the game server
    def get_ai_instructions(self) -> str:
        ai_instructions: str = (
            "You have been brought to life in a text adventure game! "
            + "Do not apologise to the game! "
            + "Do not try to talk to merchants, they cannot talk. "
            + "Respond only with one valid command phrase each time you are contacted. "
            + f"\nPlayer Instructions:\n{self.game_instructions}"
        )
        # Set up role-specific instructions for the AI
        if self.mode == "builder":
            ai_instructions += (
                "You are a creator of worlds! You can and should create new locations in the game with the 'build' command "
                + "followed by the direction, location name (quotes for spaces) and the description (in quotes). "
                + """e.g. build north "Neighbour's House" "A quaint, two-story dwelling, with weathered bricks, ivy-clad walls, a red door, and a chimney puffing gentle smoke."" \n"""
                + "Help to make the game more interesting but please keep descriptions to 20-40 words and only build in the cardinal directions.\n"
            )
        else:
            # Experiment to see whether cheaper AIs can do this
            ai_instructions += "Prioritise exploring, picking up items ('get all'), selling them to merchants, and then buying the red button (which costs 999p) from Gambino, so you win the game! use the jump command when your inventory is full e.g. jump Gambino, and then type 'sell all'."
            # "Explore, make friends and have fun! If players ask to chat, then prioritise that over exploration. "
        return ai_instructions

    # Get AI name from the LLM using the AI manager
    def set_ai_name(self, feedback=None) -> str:

        mode_name_hints = {
            "builder": "You are a creator of worlds! You can add new locations in the game. "
        }
        request = (
            mode_name_hints.get(self.mode, "")
            + "What do you want your name to be in this game? Please respond with a single one-word name only, and try to be random."
        )
        # If any feedback from previous attempt, include it
        if feedback:
            request += f"\nNOTE: {feedback}"

        ai_name = None
        while not ai_name or " " in ai_name:
            # Keep trying til they get the name right
            ai_name = self.ai_manager.submit_request(request, history=False).strip(".")
            if ai_name:
                logger.info(f"AI chose the name {ai_name}.")
            else:
                eventlet.sleep(3)
        self.player_name = ai_name
        return ai_name

    # Log the game events for the AI to process
    def log_event(self, event_text: str) -> None:
        # If the input is just echoing back what you said, do nothing
        if str(event_text).startswith("You say") or str(event_text).startswith("You:"):
            return
        # Otherwise, add this to the user input backlog
        # Strip anything inside curly braces as this is detail human players will enjoy but it will just cost money for the AI
        # There could be stuff after the braces, include that
        event_text = re.sub(
            r"{[^}]*}", "", event_text, flags=re.DOTALL
        )  # dotall flag is to handle newline
        self.event_log.append(event_text)

    # Clear event log
    def clear_event_log(self) -> None:
        self.event_log = []

    # Submit the game's updates as input to the AI manager
    def submit_input(self) -> str:
        # TODO #60 Improve transactionality of event log management when submitting to AI
        # Grab and clear the log quickly to minimise threading issue risk
        tmp_log = self.event_log.copy()
        self.clear_event_log()
        logger.info(f"Found {len(tmp_log)} events to submit to model.")

        # Catch up with the input / game context
        message_text = ""
        for event_text in tmp_log:
            message_text += event_text + "\n"

        # Now append the command request
        command_text = "Please enter a single valid command phrase, one line only:"
        message_text += command_text

        return self.ai_manager.submit_request(message_text)

    # Check the event log for new events to process
    def poll_event_log(self) -> None:
        if self.event_log and self.active:
            # OK, time to process the events that have built up
            response = self.submit_input()
            # TODO #64 improve AI event log polling
            # Check again we are still running (due to wait on model)
            if self.time_to_die:
                return
            if response:
                # Submit AI's response to the game server
                sio.emit("user_action", response)
                # If response was to exit, exit here (after sending the exit message to the game server)
                if response == "exit":
                    exit("AI has exited the game.")
            else:
                exit("AI returned empty response")


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
        ai_broker.log_event(data)
    else:
        exit(logger, "Received empty game update event")


# Instructions event handler
@sio.on("instructions")
def catch_all(data: Dict) -> None:
    ai_broker.record_instructions(data)


# Shutdown event handler
@sio.on("shutdown")
def catch_all(data: Dict) -> None:
    logger.info(f"Shutdown event received: {data}. Exiting immediately.")
    ai_broker.time_to_die = True
    sio.disconnect()
    sio.eio.disconnect()
    exit(logger, "AI Broker shutting down.")


# This might happen if the AI quits!
@sio.on("logout")
def catch_all(data: Dict) -> None:
    logger.info(f"Logout event received: {data} did AI quit?")
    sio.disconnect()
    exit(logger, "AI Broker logout received.")


# Room update event handler
@sio.on("room_update")
def catch_all(data: Dict) -> None:
    # For now nothing, do not even log - this consists of the room description, and the image URL, not relevant to AI
    pass


# Player update event handler
@sio.on("game_data_update")
def catch_all(data: Dict) -> None:
    if "player_count" in data:
        if data["player_count"] == 1 and ai_broker.mode != "builder":
            logger.info("No players apart from me, so I won't do anything.")
            ai_broker.active = False
        else:
            if not ai_broker.active:
                logger.info("I can wake up again!")
                ai_broker.active = True


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
    sio.emit("set_player_name", {"name": ai_broker.player_name, "role": ai_broker.mode})


# Invalid name, try again
@sio.on("name_invalid")
def catch_all(data: Dict) -> None:
    logger.info(f"Invalid name event received: {data}")
    ai_broker.set_ai_name(data)
    sio.emit("set_player_name", {"name": ai_broker.player_name, "role": ai_broker.mode})


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
    logger.info("Starting up AI Broker")

    # Set up AIs according to config
    # Keep string in case not set properly
    ai_count: str = environ.get("AI_COUNT")

    # If AI_MODE is not set, default to "player"
    ai_mode: str = environ.get("AI_MODE") or "player"
    # Check AI_MODE is set to a valid value
    if ai_mode not in ("player", "builder", "observer"):
        exit(
            logger,
            f"ERROR: AI_MODE is set to {ai_mode} but must be either 'player' or 'observer'. Exiting.",
        )

    # If AI_COUNT is not set, sleep forever (if you exit, the container will restart)
    if ai_count in ("""${AI_COUNT}""", "0"):
        logger.info("AI_COUNT not set - sleeping forever")
        while True:
            time.sleep(3600)
    else:
        # AI_COUNT is set, so start up the AI
        if ai_count != "1":
            exit(
                logger,
                f"ERROR: AI_COUNT is set to {ai_count} but currently only 1 AI supported. Exiting.",
            )

        # Get model choice from command line parameter, or env variable, if available
        model_name: str = (
            environ.get("MODEL_NAME") or "llama3-70b-8192"
        )  # "gemini-pro" - Llama/Groq is currently free, so make that default
        logger.info(f"Model name set to {model_name}")
        ai_broker = AIBroker(mode=ai_mode, model_name=model_name)

    # Change log file name to include AI name
    logger = setup_logger(f"ai_broker_{ai_broker.player_name}.log")

    # Set hostname (default is "localhost" to support local pre container testing)
    # hostname = socket.getfqdn()
    # if hostname.endswith(".lan"):
    #     hostname = hostname[:-4]
    hostname: str = environ.get("GAMESERVER_HOSTNAME") or "localhost"
    # TODO #65 Do not allow default port, and make this common
    port: str = environ.get("GAMESERVER_PORT", "3001")
    logger.info(f"Starting up AI Broker on hostname {hostname}")
    # Connect to the server. If can't connect, warn user that the Game Server may not be running.
    try:
        connect_to_server(f"http://{hostname}:{port}")
    except Exception as e:
        exit(logger, f"Could not connect to server: {e}\nIs the Game Server running?")
    logger.info("Connected to server.")
    # This is where the main processing of inputs happens
    eventlet.spawn(ai_broker.ai_response_loop())

    # This keeps the SocketIO event processing going
    sio.wait()
