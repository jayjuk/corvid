from typing import List, Dict, Optional
import asyncio
import time
from os import environ
import re
from utils import get_critical_env_variable, set_up_logger, exit, get_boolean_env_variable, update_logger_filename

# Set up logger before importing other modules that use it
# Assume that if an AI name is pre-set, we are calling from the Agent Manager and do not log to stdout
log_file_name: str = "AI_Broker.log"
if environ.get("AI_NAME",""):
    log_file_name = f"AI_Broker_{environ['AI_NAME']}.log"
logger = set_up_logger(log_file_name, log_to_stdout=get_boolean_env_variable("AI_BROKER_LOG_TO_STDOUT"))

from aimanager import AIManager
from messagebroker_helper import MessageBrokerHelper
import random

# Class to manage the AI's interaction with the Orchestrator
class AIBroker:

    def __init__(
        self,
        mode: str = "agent",
        model_name: str = None,
        system_message_in: Optional[str] = "",
    ) -> None:
        # Constructor
        self.mode: Optional[str] = mode
        self.time_to_exit: bool = False
        self.event_log: List[str] = []
        # AI Broker specific max history - this is the number of events to keep in the event log
        # The more events, the more context the AI has, but also the more expensive it is to process
        self.max_history: int = int(environ.get("AIBROKER_MAX_HISTORY", 100))
        # Maximum wait time in seconds between polling the event log for new events
        self.max_wait: int = int(environ.get("AIBROKER_RESPONSE_INTERVAL", 5))
        self.last_time: float = time.time()
        self.active: bool = True
        self.user_name: str = None
        self.error_count: Dict[str, int] = {}
        self.event_log_lock = asyncio.Lock()
        # Tolerance for repeated errors before exiting. Hardcoded for now.
        self.max_error_count: int = 10

        system_message: str = self.get_ai_instructions()
        if system_message_in.strip():
            system_message += (
                "\nYOUR Special Instructions (these are very important and take precedence): "
                + system_message_in.strip()
                + "\n"
            )
        self.system_message = system_message_in
        # Set up the AI manager
        self.ai_manager = AIManager(
            model_name = model_name,
            system_message = system_message,
            max_history = self.max_history,
            ai_name = environ.get("AI_NAME")
        )

    async def set_up_agent(self) -> None:
        # Set up the message broker
        self.mbh = MessageBrokerHelper(
            get_critical_env_variable("ORCHESTRATOR_HOSTNAME"),
            get_critical_env_variable("ORCHESTRATOR_PORT"),
            {
                "set_user_name": {"mode": "publish"},
                "summon_agent_response": {"mode": "publish"},
                "user_action": {"mode": "publish"},
                "world_update": {"mode": "subscribe", "callback": self.world_update},
                "logout": {"mode": "subscribe", "callback": self.logout},
                "instructions": {"mode": "subscribe", "callback": self.instructions},
                "global_shutdown": {"mode": "subscribe", "callback": self.shutdown},
                "room_update": {"mode": "subscribe", "callback": self.room_update},
                "world_data_update": {
                    "mode": "subscribe",
                    "callback": self.world_data_update,
                },
                "name_invalid": {"mode": "subscribe", "callback": self.name_invalid},
            },
        )

        # Start consuming messages
        await self.mbh.set_up_nats()

        # Get the AI's name
        await self.set_ai_name()

    # World update event handler
    async def world_update(self, data: Dict) -> None:
        if data:
            logger.info(f"Received world update event: {data}")
            self.log_event(data)
        else:
            # Take a hard line on this - it is a sign of a defect elsewhere
            logger.critical("Received empty world update event")
            self.time_to_exit = True

    # Instructions event handler
    async def instructions(self, data: Dict) -> None:
        logger.info(f"Received instructions event: {data}")
        self.record_instructions(data)

    # Shutdown event handler
    async def shutdown(self, data: Dict) -> None:
        logger.critical(f"Shutdown event received: {data}. Exiting immediately.")
        self.time_to_exit = True

    # This might happen if the AI quits!
    async def logout(self, data: Dict) -> None:
        self.time_to_exit = True
        exit(logger, f"Logout event received: {data} - either AI quit or an agent-wide logout was triggered.")

    # Room update event handler
    async def room_update(self, data: Dict) -> None:
        # For now nothing, do not even log - this consists of the room description, and the image URL, not relevant to AI
        pass

    # Person update event handler
    async def world_data_update(self, data: Dict) -> None:
        if "user_count" in data:
            if data["user_count"] == 1 and self.mode != "builder" and not get_boolean_env_variable("ALLOW_SOLO_AGENT_ACTIVITY"):
                logger.info("No people apart from me, so I won't do anything.")
                self.active = False
            else:
                if not self.active:
                    logger.info("I can wake up again!")
                    self.active = True

    # Invalid name, try again
    async def name_invalid(self, data: Dict) -> None:
        error_message: str = f"Invalid name event received: {data}"
        logger.info(error_message)
        self.log_error(error_message)
        # If AI_NAME is set in the environment and was the invalid name, reset it
        if environ.get("AI_NAME", "") in data:
            # Set AI_NAME to empty string to force a new name to be chosen
            environ["AI_NAME"] = ""
        self.set_ai_name(data)

    # The main processing loop
    async def ai_response_loop(self) -> None:
        while True:
            # Exit own thread when time comes
            if self.time_to_exit:
                logger.info("Exiting the main loop in order to exit cleanly.")
                return

            # Check if we need to wait before polling the event log
            response_interval = self.max_wait - (time.time() - self.last_time)
            if response_interval > 0:
                # don't do anything for now
                logger.info(f"{self.user_name} sleeping for {response_interval} seconds")
                await asyncio.sleep(response_interval)
            await self.poll_event_log()
            # Record time
            self.last_time = time.time()

    # AI manager will record instructions from the Orchestrator
    # Which are given to each user at the start of the world
    def record_instructions(self, data: str) -> None:
        logger.info(f"Received instructions: {data}")
        self.ai_manager.set_system_message(self.system_message + "\n" + data)

    # AI manager will get instructions from the Orchestrator
    def get_ai_instructions(self) -> str:
        ai_instructions: str = (
            "You have been brought to life in a simulated world! "
            + "Do not apologise to the world! "
            + "Do not try to talk to merchants, they cannot talk. "
            + "Respond only with one valid single-line command phrase each time you are contacted.\n"
        )
        # Set up role-specific instructions for the AI
        if self.mode == "builder":
            ai_instructions += (
                "You are a creator of worlds! You can and should create new locations in the world with the 'build' command "
                + "followed by the direction, location name (quotes for spaces) and the description (in quotes). "
                + """e.g. build north "Neighbour's House" "A quaint, two-story dwelling, with weathered bricks, ivy-clad walls, a red door, and a chimney puffing gentle smoke."" \n"""
                + "Help to make the world more interesting but please keep descriptions to 20-40 words and only build in the cardinal directions.\n"
            )
        else:
            # General instructions for all other modes
            ai_instructions += "Explore, make friends and have fun! If people ask to chat, then prioritise that over exploration. "
        return ai_instructions

    # Get AI name from the LLM using the AI manager
    async def set_ai_name(self, feedback=None) -> None:

        # If AI_NAME is set in the environment, use that
        ai_name = environ.get("AI_NAME", "")
        if " " in ai_name:
            exit(logger, "AI_NAME must not contain spaces. Exiting.")
        if ai_name:
            logger.info(f"AI_NAME is set to {ai_name}.")
        else:
            logger.info("AI_NAME is not set, letting model choose a name.")

            mode_name_hints = {
                "builder": "You are a creator of worlds! You can add new locations. "
            }
            vowels = "aeiou"
            consonants = "bcdfghjklmnpqrstvwxyz"
            random_vowel = random.choice(vowels)
            random_consonant = random.choice(consonants)

            request = (
                mode_name_hints.get(self.mode, "")
                + f"What do you want your name to be? Please respond with a single one-word name only using only alphabetical characters (letters). "
                + f"Your name should include the letters '{random_consonant}' and '{random_vowel}'."
            )
            # If any feedback from previous attempt, include it
            if feedback:
                request += f"\nNOTE: {feedback}"

            ai_name = None
            retries = 0
            max_retries = 5
            while (not ai_name or not ai_name.isalpha()) and retries < max_retries:
                # Keep trying until a valid name is chosen or max retries reached
                ai_name = (
                    self.ai_manager.submit_request(request, history=False)
                    .strip()
                    .strip(".")
                    .strip("!")
                    .strip("?")
                )
                if ai_name and ai_name.isalpha():
                    logger.info(f"AI chose the name {ai_name}.")
                else:
                    logger.warning(
                        f"Invalid AI name '{ai_name}'. Retrying ({retries+1}/{max_retries})..."
                    )
                    ai_name = None
                    retries += 1
                    await asyncio.sleep(3)
            if not ai_name:
                exit(
                    logger,
                    "Failed to obtain a valid AI name after multiple attempts. Exiting.",
                )

        # Unsubscribe from the previous name if already set
        if self.user_name:
            await self.mbh.unsubscribe(f"world_update.{self.user_id}")
            await self.mbh.unsubscribe(f"instructions.{self.user_id}")
            await self.mbh.unsubscribe(f"room_update.{self.user_id}")

        # Set the AI's name and ID
        self.user_name = ai_name
        self.user_id = self.user_name.lower()

        # Update logger filename
        update_logger_filename(logger, f"ai_broker_{self.user_name}.log", log_to_stdout = get_boolean_env_variable("AI_BROKER_LOG_TO_STDOUT"))

        # Subscribe to name-specific events
        await self.mbh.subscribe(f"world_update.{self.user_id}", self.world_update)
        await self.mbh.subscribe(f"logout.{self.user_id}", self.logout)
        await self.mbh.subscribe(f"instructions.{self.user_id}", self.instructions)
        await self.mbh.subscribe(f"room_update.{self.user_id}", self.room_update)

        await self.mbh.publish(
            "set_user_name",
            {
                "name": self.user_name,
                "role": self.mode,
                "user_id": self.user_id,
            },
        )

    # Log the world events for the AI to process
    def log_event(self, event_text: str) -> None:
        # If the input is just echoing back what you said, do nothing
        #if (
            #str(event_text).startswith("You say")
            #or str(event_text).startswith("You:")
            #or str(event_text) == "I'm trying to guess what you meant by that."
        #):
            #return
            
        # Otherwise, add this to the user input backlog
        # Strip anything inside angle brackets as this is detail human people will enjoy but it will just cost money for the AI
        # There could be stuff after the brackets, include that
        event_text = re.sub(
            r"<[^>]*>", "", event_text, flags=re.DOTALL
        )  # dotall flag is to handle newline
        self.event_log.append(event_text)

    # Submit the world's updates as input to the AI manager
    async def submit_input(self) -> str:
        # Use asyncio.Lock to protect access to self.event_log
        async with asyncio.Lock():
            # Grab and clear the log quickly to minimise threading issue risk
            tmp_log = self.event_log.copy()
            self.event_log = []
        logger.info(f"Found {len(tmp_log)} events to submit to model.")

        # Catch up with the input / world context
        message_text = "\n"
        for event_text in tmp_log:
            message_text += event_text + "\n"

        # Now append the command request
        #command_text = "\n Please enter a single valid command phrase, one line and action only:"
        #message_text += command_text

        return self.ai_manager.submit_request(message_text)

    # Check the event log for new events to process
    async def poll_event_log(self) -> None:
        if self.event_log and self.active:
            # OK, time to process the events that have built up
            response = await self.submit_input()
            # TODO #64 improve AI event log polling
            # Check again we are still running (due to wait on model)
            if self.time_to_exit:
                return
            if response:
                # Submit AI's response to the Orchestrator
                await self.mbh.publish(
                    "user_action",
                    {"user_input": response, "user_id": self.user_id},
                )
            else:
                logger.error("AI returned empty response!")
        else:
            logger.info(f"No events, active = {self.active}")

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
    # Will be redefined inside main
    global logger

    # Set up AIs according to config
    # Keep string in case not set properly
    ai_count: str = environ.get("AI_COUNT")

    # If AI_MODE is not set, default to "agent"
    ai_mode: str = environ.get("AI_MODE") or "agent"
    # Check AI_MODE is set to a valid value
    valid_ai_modes = ["agent", "builder", "monitor"]
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

        # Create AI Broker
        ai_broker = AIBroker(
            mode=ai_mode,
            model_name=get_critical_env_variable("MODEL_NAME"),
            system_message_in=environ.get("MODEL_SYSTEM_MESSAGE"),
        )

        # Set up the agent
        await ai_broker.set_up_agent()

        # This is where the main processing of inputs happens
        asyncio.create_task(ai_broker.ai_response_loop())

        # Keep the event loop running
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
