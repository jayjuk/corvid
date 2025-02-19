import asyncio
from typing import List, Dict, Optional
import eventlet
import time
from os import environ
import re
from utils import get_critical_env_variable, setup_logger, exit


from aimanager import AIManager
from messagebroker_helper import MessageBrokerHelper


# Class to manage the AI's interaction with the game server
class AIBroker:

    def __init__(
        self,
        mode: str = "player",
        model_name: str = None,
        system_message: Optional[str] = None,
    ) -> None:
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
        self.error_count: Dict[str] = {}
        self.max_error_count: int = 10

        this_system_message: str = self.get_ai_instructions()
        if system_message and system_message.strip():
            this_system_message += (
                "\nYOUR Special Instructions (these are very important and take precedence): "
                + system_message.strip()
                + "\n"
            )
        self.system_message = this_system_message
        # Set up the AI manager
        self.ai_manager = AIManager(
            model_name=model_name,
            system_message=this_system_message,
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
        self.ai_manager.set_system_message(self.game_instructions + self.system_message)

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
        # else:
        #     # Experiment to see whether cheaper AIs can do this
        #     ai_instructions += (
        #         "Prioritise exploring, picking up items ('get all'), selling them to merchants,"
        #         + " and then buying the red button (which costs 999p) from Gambino, so you win the game!"
        #         + " Use the jump command when your inventory is full e.g. jump Gambino, and then type 'sell all'."
        #     )
        # "Explore, make friends and have fun! If players ask to chat, then prioritise that over exploration. "
        return ai_instructions

    # Get AI name from the LLM using the AI manager
    def set_ai_name(self, feedback=None) -> str:

        # If AI_NAME is set in the environment, use that
        if environ.get("AI_NAME"):
            self.player_name = environ.get("AI_NAME")
            return self.player_name

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
        self.player_id = self.player_name.lower().replace(" ", "_")
        return ai_name

    # Log the game events for the AI to process
    def log_event(self, event_text: str) -> None:
        # If the input is just echoing back what you said, do nothing
        if (
            str(event_text).startswith("You say")
            or str(event_text).startswith("You:")
            or str(event_text) == "I'm trying to guess what you meant by that."
        ):
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
                    exit(logger, "AI has exited the game.")
            else:
                exit(logger, "AI returned empty response")

    # Log an error message
    def log_error(self, error_message: str) -> None:
        if error_message in self.error_count:
            self.error_count[error_message] += 1
        else:
            self.error_count[error_message] = 1
        logger.error(f"Error: {error_message}")
        if self.error_count[error_message] > self.max_error_count:
            exit(logger, f"Repeated error: {error_message}")


# Main function to start the AI Broker
async def main() -> None:

    # Game update event handler
    def game_update(data: Dict) -> None:
        if data:
            logger.info(f"Received game update event: {data}")
            ai_broker.log_event(data)
        else:
            exit(logger, "Received empty game update event")

    # Instructions event handler
    def instructions(data: Dict) -> None:
        logger.info(f"Received instructions event: {data}")
        ai_broker.record_instructions(data)

    # Shutdown event handler
    def shutdown(data: Dict) -> None:
        logger.info(f"Shutdown event received: {data}. Exiting immediately.")
        ai_broker.time_to_die = True
        exit(logger, "AI Broker shutting down.")

    # This might happen if the AI quits!
    def logout(data: Dict) -> None:
        logger.info(f"Logout event received: {data} did AI quit?")
        sio.disconnect()
        exit(logger, "AI Broker logout received.")

    # Room update event handler
    def room_update(data: Dict) -> None:
        # For now nothing, do not even log - this consists of the room description, and the image URL, not relevant to AI
        pass

    # Player update event handler
    def game_data_update(data: Dict) -> None:
        if "player_count" in data:
            if data["player_count"] == 1 and ai_broker.mode != "builder":
                logger.info("No players apart from me, so I won't do anything.")
                ai_broker.active = False
            else:
                if not ai_broker.active:
                    logger.info("I can wake up again!")
                    ai_broker.active = True

    # Invalid name, try again
    async def name_invalid(data: Dict) -> None:
        error_message: str = f"Invalid name event received: {data}"
        logger.info(error_message)
        ai_broker.log_error(error_message)
        # If AI_NAME is set in the environment and was the invalid name, reset it
        if environ.get("AI_NAME", "") in data:
            # Set AI_NAME to empty string to force a new name to be chosen
            environ["AI_NAME"] = ""
        ai_broker.set_ai_name(data)
        await mbh.emit(
            "set_player_name", {"name": ai_broker.player_name, "role": ai_broker.mode}
        )

    # Set up logger before importing other modules that use it
    logger = setup_logger("AI Broker")

    # Set up AIs according to config
    # Keep string in case not set properly
    ai_count: str = environ.get("AI_COUNT")

    # If AI_MODE is not set, default to "player"
    ai_mode: str = environ.get("AI_MODE") or "player"
    # Check AI_MODE is set to a valid value
    valid_ai_modes = ["player", "builder"]
    if ai_mode not in valid_ai_modes:
        exit(
            logger,
            f"ERROR: AI_MODE is set to {ai_mode} but must be one of: {valid_ai_modes}. Exiting.",
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

        ai_broker = AIBroker(
            mode=ai_mode,
            model_name=get_critical_env_variable("MODEL_NAME"),
            system_message=environ.get("MODEL_SYSTEM_MESSAGE"),
        )

    mbh = MessageBrokerHelper(
        environ.get("GAMESERVER_HOSTNAME", "localhost"),
        {
            "summon_player_response": {"mode": "publish"},
            "game_update": {"mode": "subscribe", "callback": game_update},
            "instructions": {"mode": "subscribe", "callback": instructions},
            "shutdown": {"mode": "subscribe", "callback": shutdown},
            "logout": {"mode": "subscribe", "callback": logout},
            "room_update": {"mode": "subscribe", "callback": room_update},
            "game_data_update": {"mode": "subscribe", "callback": game_data_update},
            "name_invalid": {"mode": "subscribe", "callback": name_invalid},
        },
    )
    # Change log file name to include AI name
    logger = setup_logger(f"ai_broker_{ai_broker.player_name}.log")

    logger.info(
        f"AI's chosen name is: {ai_broker.player_name} and this is being emitted from player_id {ai_broker.player_id}"
    )

    # Start consuming messages
    await mbh.setup_nats()

    await mbh.publish(
        "set_player_name",
        {
            "name": ai_broker.player_name,
            "role": ai_broker.mode,
            "player_id": ai_broker.player_id,
        },
    )

    # This is where the main processing of inputs happens
    eventlet.spawn(ai_broker.ai_response_loop())

    await asyncio.Event().wait()  # Keeps the event loop running


if __name__ == "__main__":
    asyncio.run(main())
