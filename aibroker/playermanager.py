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
logger = set_up_logger("Player Manager")


# Class to manage the AI's interaction with the game server
class PlayerManager:

    def __init__(
        self,
        init_filename: str,
    ) -> None:
        # Constructor

        # Read the player data from the file
        self.player_data: Dict = self.read_player_data(init_filename)

        player_count = 0

        for player in self.player_data["players"]:
            player_count += 1
            # Add the team briefing to the player data
            player["team_briefing"] = self.player_data["team_briefing"]
            logger.info(f"Creating player {player_count}")
            self.create_player(player)  # Create the player

    # Check file is JSON and parse it into a dictionary
    def read_player_data(self, filename: str) -> Dict:
        try:
            with open(filename, "r") as f:
                player_data = json.load(f)
        except FileNotFoundError:
            exit(logger, f"File not found: {filename}")
        except json.JSONDecodeError:
            exit(logger, f"File is not valid JSON: {filename}")
        return player_data

    # Create a player
    def create_player(self, player_dict: Dict) -> None:
        # Create a player
        logger.info(f"Creating player: {player_dict}")

        env_vars = {
            "MODEL_NAME": player_dict.get(
                "model_name", get_critical_env_variable("MODEL_NAME")
            ),
            "AI_NAME": "",  # Let the AI broker assign a name
            "AI_MODE": "player",
            "AI_COUNT": "1",
            "MODEL_SYSTEM_MESSAGE": os.environ.get("MODEL_SYSTEM_MESSAGE", "")
            + "\n STAY IN CHARACTER. Player Character: "
            + player_dict.get("player_briefing", ""),
        }

        def run_player_process(env_vars):

            logger.info(f"Starting player process with env vars: {env_vars}")

            env = {**os.environ, **env_vars}
            # Generate unique log file name based on timestamp
            seconds_since_epoch = str(time.time())

            log_file_name = os.path.join(
                get_logs_folder(),
                f"player_{env_vars['AI_NAME']}_{seconds_since_epoch}.log",
            )
            logger.info(f"Log file name: {log_file_name}")
            with open(log_file_name, "w") as f:
                subprocess.Popen(
                    ["python", "aibroker.py"],
                    env=env,
                    stdout=f,
                    stderr=f,
                )

        # Run the player process in a background thread

        # TODO #100 Improve solution for managing AI processes
        asyncio.create_task(asyncio.to_thread(run_player_process, env_vars))
        logger.info(f"Player created: {env_vars}")


# Main
async def main() -> None:

    async def summon_player_request(data: Dict) -> None:
        logger.info(f"Received Summon Player request: {data}")
        if "request_data" in data and "request_id" in data:
            # If data["request_data"] is a string, expect that to just be the player briefing
            if isinstance(data["request_data"], str):
                logger.info(
                    f"Assuming request is just a player briefing: {data['request_data']}"
                )
                data["request_data"] = {"player_briefing": data["request_data"]}
            new_player_name: str = player_manager.create_player(data["request_data"])
            await mbh.publish(
                "summon_player_response",
                {"request_id": data["request_id"], "player_name": new_player_name},
            )
        else:
            exit(logger, f"Invalid request data: {data}")

    mbh = MessageBrokerHelper(
        os.environ.get("GAMESERVER_HOSTNAME", "localhost"),
        {
            "summon_player_response": {"mode": "publish"},
            "summon_player_request": {
                "mode": "subscribe",
                "callback": summon_player_request,
            },
        },
    )

    # Create AI Worker
    player_manager = PlayerManager(
        init_filename=get_critical_env_variable("AI_PLAYER_FILE_NAME"),
    )

    # Start consuming messages
    await mbh.set_up_nats()

    await asyncio.Event().wait()  # Keeps the event loop running


# Main function to start the program
if __name__ == "__main__":
    asyncio.run(main())
