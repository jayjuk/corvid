import socketio
import time
import datetime
import openai
import sys
from pprint import pprint

# Register the client with the server
sio = socketio.Client()


# Simple print alternative to flush everything for now
# TODO: logging, common utils
def log(message, second_message=""):
    print(str(message) + " " + second_message, flush=True)


# Class to handle interaction with the AI
class AIManager:
    _instance = None
    game_instructions = ""
    chat_history = []
    max_wait = 10  # secs
    last_time = time.time()
    chat_count = 0
    max_chats = 300

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AIManager, cls).__new__(cls)
            # Set up openAI connection
            # We are going to use the chat interface to get AI To play our text adventure game
            api_key_file = "openai.key"

            openai.organization = "org-8c0Mch2S2vEl9vzWd5cT82gj"
            openai.api_key_path = api_key_file
            openai.Model.list()

        return cls._instance

    def record_instructions(self, data):
        self.game_instructions += data

    def get_ai_name(self):
        messages = [
            {
                "role": "system",
                "content": "You are playing an adventure game. It is set in a typical house in the modern era.",
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
            log("ERROR: AI returned empty response")
            sys.exit(1)

    def submit_input(self):
        messages = [
            {
                "role": "system",
                "content": "You are playing in a text adventure game. Explore, make friends and have fun! "
                + "It is set in a typical house. For now all you can do is move and chat. "
                + f" Respond only with one valid command or thing to say each time you are contacted. Instructions:\n{self.game_instructions}",
            }
        ]
        for history_item in self.chat_history:
            messages.append(
                {
                    "role": history_item["role"],
                    "content": history_item["content"],
                }
            )

        messages.append(
            {
                "role": "user",
                "content": "Please enter your next game command. Hint: don't leave mid chat with another player!:",
            }
        )

        # print("<<<<<<<<<<<")
        # pprint(messages)
        # print(">>>>>>>>>>>")

        return self.submit_request(messages)

    def submit_request(self, messages):
        wait_time = self.max_wait - (time.time() - self.last_time)
        if wait_time > 0:
            # don't do anything for now
            log(f"Not doing anything in the next {wait_time} seconds")
            # TODO: figure out if this is blocking the game! e.g. when another event happens. is this causing stuff to happen out of order?
            time.sleep(wait_time)
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=messages,
                max_tokens=50,  # You can adjust the max_tokens based on your desired response length
            )
        except Exception as e:
            log(f"Error from ChatGPT: {str(e)}")
            sys.exit(1)
        # Extract and print the response from ChatGPT
        chatgpt_response = response.choices[0]["message"]["content"].strip()
        log("ChatGPT Response: ", chatgpt_response)
        self.chat_count += 1

        # Stop going rogue
        if self.chat_count > self.max_chats:
            log("Too many messages sent, shutting down")
            sys.exit(1)

        # Record time
        self.last_time = time.time()

        return chatgpt_response


@sio.on("game_update")
def catch_all(data):
    if data:
        log(f"Received game update event: {data}")
        ai_manager.log_event(data)
    else:
        log("ERROR: Received empty game update event")
        sys.exit(1)


@sio.on("instructions")
def catch_all(data):
    ai_manager.record_instructions(data)


@sio.on("heartbeat")
def catch_all(data):
    # log(f"HEARTBEAT INFO (NOT SENT TO AI): {data}")
    # for now nothing
    pass


@sio.on("shutdown")
def catch_all(data):
    log(data)
    sio.disconnect()
    sys.exit(1)


@sio.on("room_update")
def catch_all(data):
    # log(f"Received room update event: {data}")
    # for now nothing
    pass


@sio.on("*")
def catch_all(event, data):
    log(f"Received other event '{event}': {data}")


@sio.event
def connect():
    log("Connected to Server.")
    ai_name = ai_manager.get_ai_name()
    sio.emit("set_player_name", ai_name)


@sio.event
def disconnect():
    log("Disconnected from Server.")


def main():
    sio.connect(
        # TODO: make this configurable
        "http://localhost:3001"
    )
    sio.wait()


if __name__ == "__main__":
    ai_manager = AIManager()
    main()
