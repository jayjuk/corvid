from typing import Dict
import os
import sys
from utils import (
    get_critical_env_variable,
    set_up_logger,
    exit,
    get_logs_folder,
    get_boolean_env_variable
)
import subprocess
import json
import time
import asyncio
from messagebroker_helper import MessageBrokerHelper

# Set up logger
logger = set_up_logger("Agent Manager")


# Class to manage the AI's interaction with the Orchestrator
class agentmanager:

    def __init__(
        self,
        init_filename: str,
        mbh: MessageBrokerHelper
    ) -> None:
        # Constructor
        self.mbh: MessageBrokerHelper = mbh

        # Read the agent data from the file
        if init_filename:
            self.user_data: Dict = self.read_user_data(init_filename)
        else:
            # Allow empty agent data - they can be summnoned later
            self.user_data = {"people": []}

        self.user_count = 0

    async def create_agents(self):
        for agent in self.user_data["people"]:
            self.user_count += 1
            # Add the team briefing to the agent data
            agent["team_briefing"] = self.user_data["team_briefing"]
            logger.info(f"Creating agent {self.user_count}")
            await self.create_agent(agent)  # Create the agent

    # Check file is JSON and parse it into a dictionary
    def read_user_data(self, filename: str) -> Dict:
        try:
            with open(filename, "r") as f:
                user_data = json.load(f)
        except FileNotFoundError:
            exit(logger, f"File not found: {filename}")
        except json.JSONDecodeError:
            exit(logger, f"File is not valid JSON: {filename}")
        return user_data

    async def logout(self, data: Dict) -> None:
        self.user_count -= 1
        logger.info(f"{data} - I now have {self.user_count} users left.")
        if self.user_count == 0 and get_boolean_env_variable("AGENT_MANAGER_SUMMON_MODE")==False:
            exit(logger, "No users left! Exiting.")

    # Create an agent
    async def create_agent(self, user_dict: Dict) -> None:
        # Create a agent
        logger.info(f"Creating agent: {user_dict}")

        user_name: str = user_dict.get("user_name", "")
        user_id: str = user_name.lower()

        env_vars = {
            "MODEL_NAME": user_dict.get(
                "model_name", get_critical_env_variable("MODEL_NAME")
            ),
            "AI_NAME": user_name,  # If blank, AI broker will assign a name
            "AI_MODE": user_dict.get("mode", "agent"),
            "AIBROKER_MAX_WAIT_TIME": user_dict.get("max_wait_time", "5"),
            "AI_COUNT": "1",
            "AI_BROKER_LOG_TO_STDOUT": "FALSE",
            "MODEL_SYSTEM_MESSAGE": os.environ.get("MODEL_SYSTEM_MESSAGE", "")
            + "\n" + "STAY IN CHARACTER. Person Character: "
            + "\n" + user_dict.get("team_briefing", "")
            + "\n" + user_dict.get("user_briefing", ""),
        }

        # Subscribe to logout message for this name
        if user_id:
            await self.mbh.subscribe(f"logout.{user_id}", self.logout)

        def run_user_process(env_vars):

            logger.info(f"Starting agent process with env vars: {env_vars}")

            env = {**os.environ, **env_vars}
            # Generate unique log file name based on timestamp
            seconds_since_epoch = str(time.time())

            log_file_name = os.path.join(
                get_logs_folder(),
                f"AI_Broker_{env_vars['AI_NAME']}_{seconds_since_epoch}_stdout.log",
            )
            logger.info(f"Log file name: {log_file_name}")
            with open(log_file_name, "w") as f:
                subprocess.Popen(
                    ["python", "aibroker.py"],
                    env=env,
                    stdout=f,
                    stderr=f,
                )

        # Run the agent process in a background thread

        # TODO #100 Improve solution for managing AI processes
        _ = asyncio.create_task(asyncio.to_thread(run_user_process, env_vars))
        logger.info(f"Person created: {env_vars}")


# Main
async def main() -> None:

    async def summon_agent_request(data: Dict) -> None:
        logger.info(f"Received Summon Person request: {data}")

        if get_boolean_env_variable("AGENT_MANAGER_SUMMON_MODE")==False:
            logger.info("Ignoring summit request as this has been disabled!")
            return

        if "request_data" in data and "request_id" in data:
            # If data["request_data"] is a string, expect that to just be the briefing
            if isinstance(data["request_data"], str):
                logger.info(
                    f"Assuming request is just a briefing: {data['request_data']}"
                )
                data["request_data"] = {"user_briefing": data["request_data"]}
            new_user_name: str = agent_manager.create_agent(data["request_data"])
            await mbh.publish(
                "summon_agent_response",
                {"request_id": data["request_id"], "user_name": new_user_name},
            )
        else:
            exit(logger, f"Invalid request data: {data}")

    # Shutdown event handler
    async def shutdown(data: str) -> None:
        logger.critical(data)
        await asyncio.sleep(3)
        sys.exit(1)

    # Shutdown event handler
    async def dummy(data: str) -> None:
        logger.info(f"dummy called???? {data}")


    # Set up the message broker
    mbh = MessageBrokerHelper(
        os.environ.get("ORCHESTRATOR_HOSTNAME", "localhost"),
        os.environ.get("ORCHESTRATOR_PORT", 4222),
        {
            "summon_agent_response": {"mode": "publish"},
            "summon_agent_request": {
                "mode": "subscribe",
                "callback": summon_agent_request,
            },
            "agent_manager_shutdown": {"mode": "subscribe", "callback": shutdown},
            "global_shutdown": {"mode": "subscribe", "callback": shutdown},
            "logout": {"mode": "subscribe", "callback": dummy},
        },
    )

    # Create AI Worker
    init_filename = os.environ.get("AI_AGENT_FILE_NAME")
    agent_manager = agentmanager(init_filename=init_filename, mbh=mbh)

    # Start consuming messages
    await mbh.set_up_nats()

    await agent_manager.create_agents()

    # Keep the event loop running
    await asyncio.Event().wait()


# Main function to start the program
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except asyncio.CancelledError:
        logger.info("Main event loop was canceled.")
    finally:
        logger.info("Closing event loop.")
