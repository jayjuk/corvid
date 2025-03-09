from typing import Dict
from os import environ
import asyncio
from utils import get_critical_env_variable, set_up_logger, exit

# Set up logger here BEFORE importing AI manager
# (registers signal handler too hence sio passed in)
logger = set_up_logger("AI Requester")

from aimanager import AIManager
from messagebroker_helper import MessageBrokerHelper


# Class to manage the AI's interaction with the game server
class AIRequester:

    def __init__(
        self,
        model_name: str,
        system_message: str,
    ) -> None:
        # Constructor
        self.model_name = model_name
        self.system_message = system_message
        # Set up the AI manager
        self.ai_manager = AIManager(
            model_name=model_name,
            system_message=system_message,
        )

    async def submit_request(self, prompt: str, system_message: str = "") -> str:
        this_system_message: str = (
            system_message if system_message else self.system_message
        )
        logger.info(
            f"Submitting request: {prompt} with system message: {this_system_message}"
        )
        response = self.ai_manager.submit_request(
            request=prompt, system_message=this_system_message, history=False
        )
        return response


# Main


async def main() -> None:

    async def catch_all(data: Dict) -> None:
        logger.info(f"Received AI request: {data}")
        if data:
            if "prompt" not in data:
                exit(logger, "Received invalid AI request")
            # Submit the request to the AI
            ai_response = await ai_requester.submit_request(
                prompt=data["prompt"],
                system_message=data.get(
                    "system_message",
                    "You are a helpful AI assistant for a game server.",
                ),
            )
            if ai_response:
                response_package = {
                    "ai_response": ai_response,
                    "request_id": data["request_id"],
                }
                # Emit event back to server
                await mbh.publish(
                    "ai_response",
                    response_package,
                )
            else:
                exit(logger, "AI request returned no response")

        else:
            exit(logger, "Received invalid event")

    # Create AI Worker
    airequester_model_name: str = environ.get(
        "AIREQUESTER_MODEL_NAME", get_critical_env_variable("MODEL_NAME")
    )
    ai_requester = AIRequester(
        # Get specific model name from environment variable or use default
        model_name=airequester_model_name,
        system_message=environ.get("MODEL_SYSTEM_MESSAGE"),
    )

    mbh = MessageBrokerHelper(
        get_critical_env_variable("GAMESERVER_HOSTNAME"),
        get_critical_env_variable("GAMESERVER_PORT"),
        {
            "ai_request": {"mode": "subscribe", "callback": catch_all},
            "ai_response": {"mode": "publish"},
        },
    )

    # Start consuming messages
    await mbh.set_up_nats()

    await asyncio.Event().wait()  # Keeps the event loop running


if __name__ == "__main__":
    asyncio.run(main())
