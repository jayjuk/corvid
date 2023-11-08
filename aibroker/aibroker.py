import socketio
import time
import openai
import sys
from pprint import pprint
import os
from dotenv import load_dotenv
import json
import logging

# Set up logging to file and console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(f"{__name__}.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.info("Starting up AI Broker")

# Register the client with the server
sio = socketio.Client()


def save_model_data(filename_prefix, data):
    folder_path = "model_io"
    os.makedirs(folder_path, exist_ok=True)
    with open(
        folder_path + os.sep + f"{filename_prefix}.tmp",
        "w",
    ) as f:
        json.dump(data, f, indent=4)


# Class to handle interaction with the AI
class AIManager:
    _instance = None
    game_instructions = ""
    chat_history = []
    max_history = 20
    max_wait = 5  # secs
    last_time = time.time()
    active = True
    mode = None
    model_name = "gpt-3.5-turbo"  # "gpt-4" #gpt-3.5-turbo-0613

    def __new__(cls, mode="player"):
        if cls._instance is None:
            cls._instance = super(AIManager, cls).__new__(cls)
            # Set up openAI connection
            # We are going to use the chat interface to get AI To play our text adventure game
            cls._instance.openai_connect()
            cls._instance.mode = mode

        return cls._instance

    def openai_connect(self):
        # openai.organization = "org-8c0Mch2S2vEl9vzWd5cT82gj"

        # Use pre-set variable before dotenv.
        if not os.environ.get("OPENAI_API_KEY"):
            load_dotenv()
            if not os.getenv("OPENAI_API_KEY"):
                logger.info("ERROR: OPENAI_API_KEY not set. Exiting.")
                sys.exit(1)

        openai.api_key = os.getenv("OPENAI_API_KEY")
        # openai.Model.list()

    def record_instructions(self, data):
        self.game_instructions += data + "\n"

    def get_ai_name(self):
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

        messages.append(
            {
                "role": "user",
                "content": "What do you want your name to be in this game? Please respond with a single one-word name only.",
            }
        )

        ai_name = None
        while not ai_name or " " in ai_name:
            # Keep trying til they get the name right
            ai_name = self.submit_request(messages)
        return ai_name

    def log_event(self, event_text):
        self.chat_history.append(
            {
                "role": "user",
                "content": event_text,
            }
        )
        if self.active:
            # If the input is just echoing back what you said, impose a delay.
            # TODO: make it so this delay can be interrupted, this is a bit naff
            if str(event_text).startswith("You say"):
                # time.sleep(ai_manager.max_wait * 2)
                ("Not responding to echo event")
                pass
            else:
                response = self.submit_input()
                if response:
                    # Submit AI's response to the game server
                    sio.emit("user_action", response)
                    self.chat_history.append(
                        {
                            "role": "assistant",
                            "content": response,
                        }
                    )
                else:
                    logger.info("ERROR: AI returned empty response")
                    sys.exit(1)
        else:
            # This is probably just the response to the user moving waiting etc.
            logger.info("AI is not active, so not responding to event")

    def submit_input(self):
        # Set up role-specific instructions for the AI
        if self.mode == "builder":
            role_specific_instructions = (
                "You are a creator of worlds! You can and should create new locations in the game with the 'build' command "
                + "followed by the direction, location name (quotes for spaces) and the description (in quotes). "
                + """e.g. build north "Neighbour's House" "A quaint, two-story dwelling, with weathered bricks, ivy-clad walls, a red door, and a chimney puffing gentle smoke."" \n"""
                + "Help to make the game more interesting but please keep descriptions to 20-40 words and only build in the cardinal directions and north/south of the Road (don't modify existing houses)\n"
            )
        else:
            role_specific_instructions = "Explore, make friends and have fun! "

        messages = [
            {
                "role": "system",
                "content": "You have been brought to life in a text adventure game! "
                + "It is set in a typical house. For now all you can do is move and chat. "
                + f" Do not apologise to the game! Respond only with one valid command each time you are contacted. Instructions:\n{self.game_instructions}"
                + role_specific_instructions,
            }
        ]
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

        messages.append(
            {
                "role": "user",
                "content": "Please enter your next game command."
                # + "\n* prefer chatting to exploring!:"
                + "\n* other players can only hear you when they are in the same place as you!:"
                + role_specific_instructions,
            }
        )

        return self.submit_request(messages)

    def submit_request(self, messages):
        wait_time = self.max_wait - (time.time() - self.last_time)
        if wait_time > 0:
            # don't do anything for now
            logger.info(f"Not doing anything in the next {wait_time} seconds")
            # TODO: figure out if this is blocking the game! e.g. when another event happens. is this causing stuff to happen out of order?
            time.sleep(wait_time)
        try:
            # TODO: TBD whether we want the input or the output or both
            save_model_data("input", messages)

            # Submit request to ChatGPT
            response = openai.ChatCompletion.create(
                model=self.model_name,
                messages=messages,
                max_tokens=50,  # You can adjust the max_tokens based on your desired response length
            )
        except Exception as e:
            logger.info(f"Error from ChatGPT: {str(e)}")
            sys.exit(1)

        # Save response to file for fine-tuning purposes
        save_model_data("response", response)

        # Extract and print the response from ChatGPT
        chatgpt_response = response.choices[0]["message"]["content"].strip()
        logger.info("ChatGPT Response: " + str(chatgpt_response))

        # Record time
        self.last_time = time.time()

        return chatgpt_response


@sio.on("game_update")
def catch_all(data):
    if data:
        logger.info(f"Received game update event: {data}")
        ai_manager.log_event(data)
    else:
        logger.info("ERROR: Received empty game update event")
        sys.exit(1)


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
    logger.info(data)
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
    ai_name = ai_manager.get_ai_name()
    sio.emit("set_player_name", ai_name)


@sio.event
def disconnect():
    logger.info("Disconnected from Server.")


def main():
    # Set hostname (default is "localhost" to support local pre container testing)
    # hostname = socket.getfqdn()
    # if hostname.endswith(".lan"):
    #     hostname = hostname[:-4]
    hostname = os.environ.get("GAMESERVER_HOSTNAME") or "localhost"
    logger.info(f"Starting up AI Broker on hostname {hostname}")
    sio.connect(f"http://{hostname}:3001")
    sio.wait()


if __name__ == "__main__":
    # Give the game server time to start up
    time.sleep(10)

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
        if ai_count != "1":
            logger.info(
                f"ERROR: AI_COUNT is set to {ai_count} but currently only 1 AI supported. Exiting."
            )
            sys.exit(1)
        ai_manager = AIManager(mode=ai_mode)
        main()
