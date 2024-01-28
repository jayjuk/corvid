import eventlet
import socketio
import time
import sys
from pprint import pprint
import os
from dotenv import load_dotenv
import json
from logger import setup_logger

# TODO: move this out to a seperate class etc, should not import both then only use one
import openai
from google.cloud import aiplatform_v1
import vertexai
from vertexai.preview.generative_models import GenerativeModel

# Register the client with the server
sio = socketio.Client()


# Connect to SocketIO server, trying again if it fails
def connect_to_server(hostname):
    connected = False
    max_wait = 120  # 2 minutes
    wait_time = 1
    while not connected and wait_time <= max_wait:
        try:
            sio.connect(hostname)
            connected = True
        except:
            logger.info(
                f"Could not connect to server. Retrying in {wait_time} seconds..."
            )
            eventlet.sleep(wait_time)
            wait_time *= 2

    if not connected:
        logger.info("Could not connect to server. Exiting.")
        sys.exit(1)


# Class to handle interaction with the AI
class AIManager:
    first_contact = True
    time_to_die = False
    _instance = None
    game_instructions = ""
    chat_history = []
    event_log = []
    max_history = 10
    max_wait = 5  # secs
    last_time = time.time()
    active = True
    mode = None
    character_name = "TBD"
    model_name = "gemini-pro"  # "gpt-3.5-turbo"  # "gpt-4" #gpt-3.5-turbo-0613
    max_tokens = 200  # adjust the max_tokens based on desired response length
    ai_name = None

    def __new__(cls, mode="player"):
        if cls._instance is None:
            cls._instance = super(AIManager, cls).__new__(cls)
            # Set up openAI connection
            # We are going to use the chat interface to get AI To play our text adventure game
            cls._instance.model_api_connect()
            cls._instance.mode = mode

            # Override max history for Gemini for now, as it's free
            if cls._instance.get_model_api() == "Gemini":
                cls._instance.max_history = 99999

            # Get the AI's name
            cls._instance.ai_name = cls._instance.get_ai_name()

        return cls._instance

    def get_model_api(self):
        # Use the specific model name to generalise which class/company we are using
        if self.model_name.startswith("gpt"):
            return "GPT"
        elif self.model_name.startswith("gemini"):
            return "Gemini"

    def model_client_manages_history(self):
        if self.get_model_api() == "Gemini":
            return True
        return False

    def save_model_data(self, filename_prefix, data):
        print("Saving model data")
        folder_path = "model_io"
        os.makedirs(folder_path, exist_ok=True)
        with open(
            folder_path + os.sep + f"{self.character_name}_{filename_prefix}.tmp",
            "w",
        ) as f:
            json.dump(data, f, indent=4)

    def model_api_connect(self):
        # Use pre-set variable before dotenv.
        if self.get_model_api() == "GPT":
            if not os.environ.get("OPENAI_API_KEY"):
                load_dotenv()
                if not os.getenv("OPENAI_API_KEY"):
                    logger.info("ERROR: OPENAI_API_KEY not set. Exiting.")
                    sys.exit(1)

            openai.api_key = os.getenv("OPENAI_API_KEY")
            self.model_client = openai.OpenAI()
        elif self.get_model_api() == "Gemini":
            # If env variable not set and file exists, set it
            # set GOOGLE_APPLICATION_CREDENTIALS=
            gcloud_credentials_file = "gemini.key"
            if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
                if not os.path.exists(gcloud_credentials_file):
                    print(
                        "GOOGLE_APPLICATION_CREDENTIALS not set and {} does not exist".format(
                            gcloud_credentials_file
                        )
                    )
                    exit()
                else:
                    print(
                        "Setting GOOGLE_APPLICATION_CREDENTIALS to {}".format(
                            gcloud_credentials_file
                        )
                    )
                    os.environ[
                        "GOOGLE_APPLICATION_CREDENTIALS"
                    ] = gcloud_credentials_file

            vertexai.init(project="jaysgame", location="us-central1")
            self.model_client = GenerativeModel("gemini-pro")
            self.chat = self.model_client.start_chat(history=[])

        else:
            logger.info(f"ERROR: Model name {self.model_name} not recognised. Exiting.")
            sys.exit(1)

    # AI manager will record instructions from the game server
    # Which are given to each player at the start of the game
    def record_instructions(self, data):
        self.game_instructions += data + "\n"

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
            role_specific_instructions = "Explore, make friends and have fun! If players ask to chat, then prioritise that over exploration. "

        return self.game_instructions + role_specific_instructions

    def get_ai_name(self):
        # TODO - improve this so builder works for Gemini and we don't switch on model, the messages construction needs to be centralised

        system_message = "You are playing an adventure game. It is set in a typical house in the modern era."
        if self.mode == "builder":
            system_message += (
                " You are a creator of worlds! You can add new locations in the game."
            )

        messages = [
            {
                "role": "system",
                "content": system_message,
            }
        ]

        name_message = "What do you want your name to be in this game? Please respond with a single one-word name only, and try to be random."
        messages.append(
            {
                "role": "user",
                "content": name_message,
            }
        )

        message_text = None
        if self.model_client_manages_history():
            message_text = system_message + name_message

        ai_name = None
        while not ai_name or " " in ai_name:
            # Keep trying til they get the name right
            ai_name = self.submit_request(messages, message_text).strip(".")
            # Reset so the intro is done again
            # TODO - improve this
            self.first_contact = False
            logger.info(f"AI chose the name {ai_name}.")
            self.character_name = ai_name
        return ai_name

    def log_event(self, event_text):
        # If the input is just echoing back what you said, do nothing
        if str(event_text).startswith("You say"):
            return
        # Otherwise, add this to the user input backlog
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
                    sys.exit(1)
                self.chat_history.append(
                    {
                        "role": "assistant",
                        "content": response,
                    }
                )
            else:
                logger.info("ERROR: AI returned empty response")
                sys.exit(1)

    def submit_input(self):
        # TODO: review this in case there is a better way
        # Grab and clear the log quickly to minimise threading issue risk
        tmp_log = self.event_log.copy()
        self.event_log = []
        print(f"Found {len(tmp_log)} events to submit to model.")

        intro_text = (
            "You have been brought to life in a text adventure game! "
            + "It is set in a typical house. For now all you can do is move and chat. "
            + f" Do not apologise to the game! Respond only with one valid command "
            + f"each time you are contacted.\nInstructions:\n{self.get_instructions()}"
        )
        command_text = (
            "Please enter your a valid command per the instructions given previously."
        )

        # Assume that if the client manages history, it just takes a string as input
        if self.model_client_manages_history():
            message_text = ""
            if self.first_contact:
                message_text += intro_text
                self.first_contact = False
            for event_text in tmp_log:
                message_text += event_text + "\n"
            message_text += command_text
            return self.submit_request(None, message_text)
        else:
            # Add the history
            # Assume for now that API clients that need history use the OpenAI role/content structure below
            for event_text in tmp_log:
                self.chat_history.append(
                    {
                        "role": "user",
                        "content": event_text,
                    }
                )

            # Now use history to build the messages for model input
            messages = [{"role": "system", "content": intro_text}]
            if len(self.chat_history) > self.max_history:
                messages.append(
                    {
                        "role": "user",
                        "content": "(some game transcript history removed for brevity))",
                    }
                )
            for history_item in self.chat_history[-1 * self.max_history :]:
                messages.append(
                    {
                        "role": history_item["role"],
                        "content": history_item["content"],
                    }
                )

            messages.append({"role": "user", "content": command_text})

            return self.submit_request(messages)

    def submit_request(self, messages, message_text=None):
        # logger.debug(f"submit_request called, {messages=}")
        try_count = 0
        model_response = None
        retries = 0
        while not model_response and retries < 3:
            retries += 1
            response = None
            try:
                # Submit request to ChatGPT
                logger.info(f"Submitting request to model...")
                if self.model_name.startswith("gpt"):
                    response = self.model_client.chat.completions.create(
                        model=self.model_name,
                        messages=messages,
                        max_tokens=self.max_tokens,
                    )
                    # Extract response content
                    for choice in response.choices:
                        model_response = choice.message.content
                        break
                elif self.model_name.startswith("gemini"):
                    # Gemini does not support system message
                    message_to_send = message_text
                    logging.info("FINAL GEMINI INPUT:\n" + message_to_send)
                    model_response = self.chat.send_message(message_to_send)
                    logging.info("ORIGINAL GEMINI RESPONSE:\n" + str(model_response))
                    model_response = model_response.text.strip("*").strip()
                    # If the response contains newline(s) followed by some info in parentheses, strip all this out
                    if "\n(" in model_response and model_response.endswith(")"):
                        model_response = model_response.split("\n")[0].strip()
                    # Convert all-upper-case response to natural case
                    if model_response.isupper():
                        model_response = model_response.title()
                    break
            except Exception as e:
                if (
                    "server is overloaded" in str(e)
                    or "The response was blocked." in str(e)
                ) and try_count < 10:
                    logger.info(f"Error from model: {str(e)}")
                    logger.info(f"Retrying in 5 seconds... (attempt {try_count+1}/3)")
                    time.sleep(5)
                    try_count += 1
                else:
                    logger.info(f"Error from model: {str(e)}")
                    return "exit"

        if response:
            # Save response to file for fine-tuning purposes
            pass
            # TODO: TBD whether we want the input or the output or both
            # self.save_model_data("input", messages)
            # self.save_model_data("response", response)

        logger.info("Model Response: " + str(model_response))

        return model_response

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


@sio.on("game_update")
def catch_all(data):
    if data:
        logger.info(f"Received game update event: {data}")
        ai_manager.log_event(data)
    else:
        logger.info("ERROR: Received empty game update event")
        sys.exit()


@sio.on("instructions")
def catch_all(data):
    ai_manager.record_instructions(data)


@sio.on("heartbeat")
def catch_all(data):
    # logger.info(f"HEARTBEAT INFO (NOT SENT TO AI): {data}")
    # for now nothing
    pass


@sio.on("shutdown")
def catch_all(data):
    logger.info(f"Shutdown event received: {data}. Exiting immediately.")
    ai_manager.time_to_die = True
    sio.disconnect()
    sio.eio.disconnect()
    sys.exit(1)


# This might happen if the AI quits!
@sio.on("logout")
def catch_all(data):
    logger.info(f"Logout event received: {data} did AI quit?")
    sio.disconnect()
    sys.exit(1)


@sio.on("room_update")
def catch_all(data):
    # logger.info(f"Received room update event: {data}")
    # for now nothing
    pass


@sio.on("game_data_update")
def catch_all(data):
    if "player_count" in data:
        if data["player_count"] == 1 and ai_manager.mode != "builder":
            logger.info("No players apart from me, so I won't do anything.")
            ai_manager.active = False
        else:
            if not ai_manager.active:
                logger.info("I can wake up again!")
                ai_manager.active = True


@sio.on("*")
def catch_all(event, data):
    logger.info(f"Received other event '{event}': {data}")


@sio.event
def connect():
    logger.info("Connected to Server.")
    # Emit the AI's chosen name to the server
    sio.emit("set_player_name", {"name": ai_manager.ai_name, "role": ai_manager.mode})


@sio.event
def connect_error(data):
    logger.error("Connection failure!")
    logger.info(data)
    sys.exit(1)


@sio.event
def disconnect():
    logger.info("Disconnected from Server.")


if __name__ == "__main__":
    # Set up logging to file and console
    logger = setup_logger("ai_broker.log")
    logger.info("Starting up AI Broker")

    # Set up AIs according to config
    ai_count = os.environ.get("AI_COUNT")

    ai_mode = os.environ.get("AI_MODE") or "player"
    if ai_mode not in ("player", "builder", "observer"):
        logger.info(
            f"ERROR: AI_MODE is set to {ai_mode} but must be either 'player' or 'observer'. Exiting."
        )
        sys.exit(1)

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
            sys.exit(1)
        ai_manager = AIManager(mode=ai_mode)

    # Change log file name to include AI name
    logger = setup_logger(f"ai_broker_{ai_manager.ai_name}.log")

    # Set hostname (default is "localhost" to support local pre container testing)
    # hostname = socket.getfqdn()
    # if hostname.endswith(".lan"):
    #     hostname = hostname[:-4]
    hostname = os.environ.get("GAMESERVER_HOSTNAME") or "localhost"
    logger.info(f"Starting up AI Broker on hostname {hostname}")
    # Connect to the server
    connect_to_server(f"http://{hostname}:3001")

    # This is where the main processing of inputs happens
    eventlet.spawn(ai_manager.ai_response_loop())

    # This keeps the SocketIO event processing going
    sio.wait()
