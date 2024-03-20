from logger import setup_logger

# Set up logger
logger = setup_logger("aibroker")

import eventlet
import socketio
import time
import sys
from os import environ
import re
from aimanager import AIManager

# Register the client with the server
sio = socketio.Client()


class AIBroker:
    time_to_die = False
    game_instructions = ""
    event_log = []
    max_history = 50
    max_wait = 3  # secs
    last_time = time.time()
    active = True
    mode = None
    player_name = "TBD"
    input_token_count = 0
    output_token_count = 0

    def __init__(self, mode="player"):
        self.mode = mode

        intro_text = (
            "You have been brought to life in a text adventure game! "
            + "For now all you can do is move and chat. "
            + "Do not apologise to the game! Respond only with one valid command phrase "
            + f"each time you are contacted.\nInstructions:\n{self.get_instructions()}"
        )

        # Set up the AI manager
        self.ai_manager = AIManager(system_message=intro_text)

        # Get the AI's name
        self.player_name = self.get_ai_name()

    # The main processing loop
    def ai_response_loop(self):
        while True:
            # Exit own thread when time comes
            if self.time_to_die:
                return

            wait_time = self.max_wait - (time.time() - self.last_time)
            if wait_time > 0:
                # don't do anything for now
                eventlet.sleep(wait_time)
            self.poll_event_log()
            # Record time
            self.last_time = time.time()

    # AI manager will record instructions from the game server
    # Which are given to each player at the start of the game
    def record_instructions(self, data):
        self.game_instructions += data + "\n"
        self.ai_manager.set_system_message(self.game_instructions)

    def get_instructions(self):
        # Set up role-specific instructions for the AI
        if self.mode == "builder":
            role_specific_instructions = (
                "You are a creator of worlds! You can and should create new locations in the game with the 'build' command "
                + "followed by the direction, location name (quotes for spaces) and the description (in quotes). "
                + """e.g. build north "Neighbour's House" "A quaint, two-story dwelling, with weathered bricks, ivy-clad walls, a red door, and a chimney puffing gentle smoke."" \n"""
                + "Help to make the game more interesting but please keep descriptions to 20-40 words and only build in the cardinal directions and north/south of the Road (don't modify existing houses)\n"
            )
        else:
            role_specific_instructions = "Prioritise finding objects (you can carry up to five in inventory), selling them to merchants, and then buying the red button from Gambino, so you win the game! do not talk to anyone. use the jump command when your inventory is full e.g. jump Gambino, and then type sell [thing]. use inventory command to see your inventory. Good luck."  # "Explore, make friends and have fun! If players ask to chat, then prioritise that over exploration. "

        return self.game_instructions + role_specific_instructions

    def get_ai_name(self):

        mode_name_hints = {
            "builder": "You are a creator of worlds! You can add new locations in the game. "
        }
        request = (
            mode_name_hints.get(self.mode, "")
            + "What do you want your name to be in this game? Please respond with a single one-word name only, and try to be random."
        )

        ai_name = None
        while not ai_name or " " in ai_name:
            # Keep trying til they get the name right
            ai_name = self.ai_manager.submit_request(request).strip(".")
            if ai_name:
                logger.info(f"AI chose the name {ai_name}.")
            else:
                eventlet.sleep(3)
        return ai_name

    def submit_input(self):
        # TODO: review this in case there is a better way
        # Grab and clear the log quickly to minimise threading issue risk
        tmp_log = self.event_log.copy()
        self.event_log = []
        logger.info(f"Found {len(tmp_log)} events to submit to model.")

        # Catch up with the input / game context
        message_text = ""
        for event_text in tmp_log:
            message_text += event_text + "\n"

        # Now append the command request
        command_text = "Please enter a single valid command phrase, one line only:"
        message_text += command_text

        return self.ai_manager.submit_request(message_text)

    def log_event(self, event_text):
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

    def poll_event_log(self):
        if self.event_log and self.active:
            # OK, time to process the events that have built up
            response = self.submit_input()
            # TODO: clean this up
            # Check again we are still running (due to wait on model)
            if self.time_to_die:
                return
            if response:
                # Submit AI's response to the game server
                sio.emit("user_action", response)
                # If response was to exit, exit here (after sending the exit message to the game server)
                if response == "exit":
                    logger.info("AI has exited the game.")
                    sys.exit()
            else:
                logger.info("ERROR: AI returned empty response")
                sys.exit()


# Connect to SocketIO server, trying again if it fails
def connect_to_server(hostname):
    connected = False
    max_wait = 240  # 4 minutes
    wait_time = 1
    while not connected and wait_time <= max_wait:
        try:
            sio.connect(hostname)
            connected = True
        except ConnectionError:
            logger.info(
                f"Could not connect to server. Retrying in {wait_time} seconds..."
            )
            eventlet.sleep(wait_time)
            wait_time = int(wait_time * 1.5)

    if not connected:
        logger.info("Could not connect to server. Exiting.")
        sys.exit()


@sio.on("game_update")
def catch_all(data):
    if data:
        logger.info(f"Received game update event: {data}")
        ai_broker.log_event(data)
    else:
        logger.info("ERROR: Received empty game update event")
        sys.exit()


@sio.on("instructions")
def catch_all(data):
    ai_broker.record_instructions(data)


@sio.on("heartbeat")
def catch_all(data):
    # logger.info(f"HEARTBEAT INFO (NOT SENT TO AI): {data}")
    # for now nothing
    pass


@sio.on("shutdown")
def catch_all(data):
    logger.info(f"Shutdown event received: {data}. Exiting immediately.")
    ai_broker.time_to_die = True
    sio.disconnect()
    sio.eio.disconnect()
    sys.exit()


# This might happen if the AI quits!
@sio.on("logout")
def catch_all(data):
    logger.info(f"Logout event received: {data} did AI quit?")
    sio.disconnect()
    sys.exit()


@sio.on("room_update")
def catch_all(data):
    # logger.info(f"Received room update event: {data}")
    # for now nothing
    pass


@sio.on("game_data_update")
def catch_all(data):
    if "player_count" in data:
        if data["player_count"] == 1 and ai_broker.mode != "builder":
            logger.info("No players apart from me, so I won't do anything.")
            ai_broker.active = False
        else:
            if not ai_broker.active:
                logger.info("I can wake up again!")
                ai_broker.active = True


@sio.on("*")
def catch_all(event, data):
    logger.info(f"Received other event '{event}': {data}")


@sio.event
def connect():
    logger.info("Connected to Server.")
    # Emit the AI's chosen name to the server
    sio.emit("set_player_name", {"name": ai_broker.player_name, "role": ai_broker.mode})


@sio.event
def connect_error(data):
    logger.error("Connection failure!")
    logger.info(data)
    sys.exit()


@sio.event
def disconnect():
    logger.info("Disconnected from Server.")


if __name__ == "__main__":
    # Set up logging to file and console
    logger.info("Starting up AI Broker")

    # Set up AIs according to config
    ai_count = environ.get("AI_COUNT")

    ai_mode = environ.get("AI_MODE") or "player"
    if ai_mode not in ("player", "builder", "observer"):
        logger.info(
            f"ERROR: AI_MODE is set to {ai_mode} but must be either 'player' or 'observer'. Exiting."
        )
        sys.exit()

    # If AI_COUNT is not set, sleep forever (if you exit, the container will restart)
    if ai_count in ("""${AI_COUNT}""", "0"):
        logger.info("AI_COUNT not set - sleeping forever")
        while True:
            time.sleep(3600)
    else:
        # AI_COUNT is set, so start up the AI
        if ai_count != "1":
            logger.info(
                f"ERROR: AI_COUNT is set to {ai_count} but currently only 1 AI supported. Exiting."
            )
            sys.exit()
        ai_broker = AIBroker(mode=ai_mode)

    # Change log file name to include AI name
    logger = setup_logger(f"ai_broker_{ai_broker.player_name}.log")

    # Set hostname (default is "localhost" to support local pre container testing)
    # hostname = socket.getfqdn()
    # if hostname.endswith(".lan"):
    #     hostname = hostname[:-4]
    hostname = environ.get("GAMESERVER_HOSTNAME") or "localhost"
    # TODO: do not allow default port, and make this common
    port = environ.get("GAMESERVER_PORT", "3001")
    logger.info(f"Starting up AI Broker on hostname {hostname}")
    # Connect to the server
    connect_to_server(f"http://{hostname}:{port}")

    # This is where the main processing of inputs happens
    eventlet.spawn(ai_broker.ai_response_loop())

    # This keeps the SocketIO event processing going
    sio.wait()
