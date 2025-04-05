import asyncio
import signal
from utils import set_up_logger, exit
from typing import List, Dict
from utils import get_critical_env_variable
from messagebroker_helper import MessageBrokerHelper

# Set up logger
logger = set_up_logger("cliclient")

# Global person name
user_name = None


async def main() -> None:
    # Define a function to handle the SIGINT signal
    def handle_sigint(signal, frame):
        asyncio.create_task(logout({"reason": "Ctrl-C"}))

    # Register the SIGINT handler
    signal.signal(signal.SIGINT, handle_sigint)

    # Get name from the person
    async def set_user_name() -> str:
        user_name = None
        while not user_name or " " in user_name:
            # Keep trying til they get the name right
            user_name = input("What do you want your name to be?").strip(".")
        # Subscribe to name-specific events
        await mbh.subscribe(f"world_update.{user_name}", world_update)
        await mbh.subscribe(f"logout.{user_name}", logout)
        await mbh.subscribe(f"instructions.{user_name}", instructions)
        await mbh.subscribe(f"room_update.{user_name}", room_update)
        # Publish name
        await mbh.publish("set_user_name", {"name": user_name, "role": "person"})
        return user_name

    # MBH event handlers

    # World update event handler
    async def world_update(data: Dict) -> None:
        if data:
            logger.info(f"Received world update event: {data}")
            print(data)
        else:
            exit(logger, "Received empty world update event")

    # Instructions event handler
    async def instructions(data: Dict) -> None:
        print(data)

    # Shutdown event handler
    async def shutdown(data: Dict) -> None:
        logger.info(f"Shutdown event received: {data}. Exiting immediately.")
        exit(logger, "Shutting down.")

    # This might happen if the AI quits!
    async def logout(data: Dict) -> None:
        logger.info(f"Logout event received: {data} did you quit?")
        await mbh.publish("logout", {"reason": data.get("reason", "unknown")})
        exit(logger, "Logout received.")

    # Room update event handler
    async def room_update(data: Dict) -> None:
        print("ROOM UPDATE:", data)

    # Person update event handler
    async def world_data_update(data: Dict) -> None:
        pass  # print("WORLD UPDATE:", data)

    # Invalid name, try again
    async def name_invalid(data: Dict) -> None:
        logger.info(f"Invalid name event received: {data}")
        await mbh.unsubscribe(f"world_update.{user_name}")
        await mbh.unsubscribe(f"logout.{user_name}")
        await mbh.unsubscribe(f"instructions.{user_name}")
        await mbh.unsubscribe(f"room_update.{user_name}")

        user_name = set_user_name()
        await mbh.publish("set_user_name", {"name": user_name, "role": "person"})

    mbh = MessageBrokerHelper(
        get_critical_env_variable("ORCHESTRATOR_HOSTNAME"),
        get_critical_env_variable("ORCHESTRATOR_PORT"),
        {
            "set_user_name": {"mode": "publish"},
            "user_action": {"mode": "publish"},
            "world_update": {"mode": "subscribe", "callback": world_update},
            "instructions": {"mode": "subscribe", "callback": instructions},
            "shutdown": {"mode": "subscribe", "callback": shutdown},
            "logout": {"mode": "both", "callback": logout},
            "room_update": {"mode": "subscribe", "callback": room_update},
            "world_data_update": {"mode": "subscribe", "callback": world_data_update},
            "name_invalid": {"mode": "subscribe", "callback": name_invalid},
        },
    )

    # Start consuming messages
    await mbh.set_up_nats()

    user_name = await set_user_name()

    # Main loop
    while True:
        action = input("What do you want to do? ").strip()
        if action:
            await mbh.publish(
                "user_action", {"user_id": user_name, "user_input": action}
            )
        else:
            print("You must enter an action.")


# Main function to start the AI Broker
if __name__ == "__main__":
    asyncio.run(main())
