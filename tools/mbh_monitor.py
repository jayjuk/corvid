import asyncio
from messagebroker_helper import MessageBrokerHelper
from utils import get_critical_env_variable, set_up_logger
import os

os.environ["LOGGER_LOG_LEVEL"] = "DEBUG"
logger = set_up_logger("Message Broker Monitor")

async def main() -> None:

    # Set up the message broker
    async def global_handler(data):
        print(data)
    mbh = MessageBrokerHelper(
        get_critical_env_variable("ORCHESTRATOR_HOSTNAME"),
        get_critical_env_variable("ORCHESTRATOR_PORT"),
        {
            "ai_request": {"mode": "subscribe", "callback": global_handler},
            "ai_response": {"mode": "subscribe", "callback": global_handler},
            "summon_agent_response": {
                "mode": "subscribe",
                "callback": global_handler,
            },
            "user_disconnect": {
                "mode": "subscribe",
                "callback": global_handler,
            },
            "instructions": {"mode": "subscribe", "callback": global_handler},
            "name_invalid": {"mode": "subscribe", "callback": global_handler},
            "global_shutdown": {"mode": "subscribe", "callback": global_handler},
            "logout": {"mode": "subscribe", "callback": global_handler},
            "room_update": {"mode": "subscribe", "callback": global_handler},
            "world_update": {"mode": "subscribe", "callback": global_handler},
            "set_user_name": {"mode": "subscribe", "callback": global_handler},
            "user_action": {"mode": "subscribe", "callback": global_handler},
        },
        
    )

    # Ready to Start consuming messages
    await mbh.set_up_nats()


    # Keep the event loop running
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
