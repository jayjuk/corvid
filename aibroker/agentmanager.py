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
        init_filename: str
    ) -> None:

        # Read the agent data from the file
        if init_filename:
            self.user_data: Dict = self.read_user_data(init_filename)
        else:
            # Allow empty agent data - they can be summnoned later
            self.user_data = {"agents": []}

        self.user_count = 0

        # Record previous instructions
        self.previous_instructions: str = ""


    # Set up MBH
    async def set_up_mbh(self) -> None:

        # Set up the message broker
        self.mbh = MessageBrokerHelper(
            os.environ.get("ORCHESTRATOR_HOSTNAME", "localhost"),
            os.environ.get("ORCHESTRATOR_PORT", 4222),
            {
                "summon_agent_response": {"mode": "publish"},
                "summon_agent_request": {
                    "mode": "subscribe",
                    "callback": self.summon_agent_request,
                },
                "agent_manager_shutdown": {"mode": "subscribe", "callback": self.shutdown},
                "global_shutdown": {"mode": "subscribe", "callback": self.shutdown},
                "world_data_update": {"mode": "subscribe", "callback": self.world_data_update},
                # This is replaced by user-specific logout instructions
                "logout": {"mode": "subscribe", "callback": self.handle_logout_placeholder},
            },
        )
        # Start consuming messages
        await self.mbh.set_up_nats()


    async def create_agents(self):
        for agent in self.user_data["agents"]:
            self.user_count += 1
            logger.info(f"Creating agent {self.user_count}")

            # Default previous instructions?
            if str(agent.get("instructions", "")).lower().startswith("ditto") and self.previous_instructions:
                logger.info(f"Repeating previous instructions: {self.previous_instructions}")
                agent["instructions"] = self.previous_instructions
            elif not (agent.get("instructions")):
                if self.user_data.get("instructions"):
                    agent["instructions"] = self.user_data["instructions"]
                else:
                    exit(logger, "All agents must have instructions, either at the group or individual level.")

            await self.create_agent(agent)  # Create the agent
            
            # Remember last instructions
            self.previous_instructions = agent["instructions"]

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
        #self.user_count -= 1
        #logger.info(f"{data} - I now have {self.user_count} users left.")
        #if self.user_count == 0 and get_boolean_env_variable("AGENT_MANAGER_SUMMON_MODE")==False:
        #    exit(logger, "No users left! Exiting.")
        logger.info(f"Logout message received by agent manager")

    # Create an agent
    async def create_agent(self, user_dict: Dict) -> None:
        # Create a agent
        user_name: str = user_dict.get("user_name", "")
        user_id: str = user_name.lower()
        logger.info(f"Creating agent {user_name}")

        env_vars = {
            "MODEL_NAME": user_dict.get(
                "model_name", get_critical_env_variable("MODEL_NAME")
            ),
            "AI_NAME": user_name,  # If blank, AI broker will assign a name
            "AI_MODE": user_dict.get("mode", "agent"),
            "AIBROKER_RESPONSE_INTERVAL": user_dict.get("response_interval", "5"),
            "AI_COUNT": "1",
            "AI_BROKER_LOG_TO_STDOUT": "FALSE",
            "MODEL_SYSTEM_MESSAGE": os.environ.get("MODEL_SYSTEM_MESSAGE", "")
            + "\n" + "Agent persona: "
            # Add the common instructions to the agent data unless overridden            
            + "\n" + user_dict["instructions"]
            + "\n" + user_dict.get("additional_instructions", ""),
        }

        # Subscribe to logout message for this name
        if user_id:
            await self.mbh.subscribe(f"logout.{user_id}", self.logout)

        def run_user_process(env_vars):

            logger.info(f"Starting agent process for agent {env_vars.get('AI_NAME')}")

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
        logger.info(f"Person created: {env_vars['AI_NAME']}")


    async def summon_agent_request(self, data: Dict) -> None:
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
                data["request_data"] = {"additional_instructions": data["request_data"]}
            new_user_name: str = self.create_agent(data["request_data"])
            await self.mbh.publish(
                "summon_agent_response",
                {"request_id": data["request_id"], "user_name": new_user_name},
            )
        else:
            exit(logger, f"Invalid request data: {data}")

    # Shutdown event handler
    async def shutdown(self, data: str) -> None:
        logger.critical(data)
        await asyncio.sleep(3)
        sys.exit(1)

    # Shutdown event handler
    async def handle_logout_placeholder(self, data: str) -> None:
        logger.info(f"dummy called???? {data}")

    async def world_data_update(self, data: Dict) -> None:
        if "user_count" in data:
            self.user_count = data["user_count"]
            logger.info(f"World data update received: there are now {self.user_count} users online.")
            if self.user_count == 0 and get_boolean_env_variable("AGENT_MANAGER_SUMMON_MODE")==False:
                exit(logger, "No users left! Exiting.")
        else:
            exit(logger, "Invalid world data update message! Exiting.")


# Main
async def main() -> None:

    # Create AI Worker
    init_filename = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("AI_AGENT_FILE_NAME")
    agent_manager = agentmanager(init_filename=init_filename)

    await agent_manager.set_up_mbh()

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
