from typing import Dict
import os
from utils import (
    get_critical_env_variable,
    set_up_logger,
    exit,
    get_logs_folder,
)
import subprocess
import json
import time
import asyncio
from messagebroker_helper import MessageBrokerHelper

# Set up logger
logger = set_up_logger("Person Manager")


# Class to manage the AI's interaction with the Orchestrator
class agentmanager:

    def __init__(
        self,
        init_filename: str,
    ) -> None:
        # Constructor

        # Read the agent data from the file
        if init_filename:
            self.user_data: Dict = self.read_user_data(init_filename)
        else:
            # Allow empty agent data - they can be summnoned later
            self.user_data = {"people": []}

        user_count = 0

        for agent in self.user_data["people"]:
            user_count += 1
            # Add the team briefing to the agent data
            agent["team_briefing"] = self.user_data["team_briefing"]
            logger.info(f"Creating agent {user_count}")
            self.create_agent(agent)  # Create the agent

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

    # Create an agent
    def create_agent(self, user_dict: Dict) -> None:
        # Create a agent
        logger.info(f"Creating agent: {user_dict}")

        env_vars = {
            "MODEL_NAME": user_dict.get(
                "model_name", get_critical_env_variable("MODEL_NAME")
            ),
            "AI_NAME": "",  # Let the AI broker assign a name
            "AI_MODE": "agent",
            "AI_COUNT": "1",
            "MODEL_SYSTEM_MESSAGE": os.environ.get("MODEL_SYSTEM_MESSAGE", "")
            + "\n STAY IN CHARACTER. Person Character: "
            + user_dict.get("user_briefing", ""),
        }

        def run_user_process(env_vars):

            logger.info(f"Starting agent process with env vars: {env_vars}")

            env = {**os.environ, **env_vars}
            # Generate unique log file name based on timestamp
            seconds_since_epoch = str(time.time())

            log_file_name = os.path.join(
                get_logs_folder(),
                f"user_{env_vars['AI_NAME']}_{seconds_since_epoch}.log",
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
        asyncio.create_task(asyncio.to_thread(run_user_process, env_vars))
        logger.info(f"Person created: {env_vars}")


# Main
async def main() -> None:

    async def summon_agent_request(data: Dict) -> None:
        logger.info(f"Received Summon Person request: {data}")
        if "request_data" in data and "request_id" in data:
            # If data["request_data"] is a string, expect that to just be the briefing
            if isinstance(data["request_data"], str):
                logger.info(
                    f"Assuming request is just a briefing: {data['request_data']}"
                )
                data["request_data"] = {"user_briefing": data["request_data"]}
            new_user_name: str = user_manager.create_agent(data["request_data"])
            await mbh.publish(
                "summon_agent_response",
                {"request_id": data["request_id"], "user_name": new_user_name},
            )
        else:
            exit(logger, f"Invalid request data: {data}")

    mbh = MessageBrokerHelper(
        os.environ.get("ORCHESTRATOR_HOSTNAME", "localhost"),
        os.environ.get("ORCHESTRATOR_PORT", 4222),
        {
            "summon_agent_response": {"mode": "publish"},
            "summon_agent_request": {
                "mode": "subscribe",
                "callback": summon_agent_request,
            },
        },
    )

    # Create AI Worker
    init_filename = os.environ.get("AI_AGENT_FILE_NAME")
    user_manager = agentmanager(init_filename=init_filename)

    # Start consuming messages
    await mbh.set_up_nats()

    await asyncio.Event().wait()  # Keeps the event loop running


# Main function to start the program
if __name__ == "__main__":
    asyncio.run(main())
