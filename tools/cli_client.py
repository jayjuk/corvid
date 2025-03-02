import asyncio
import signal
from utils import set_up_logger, exit
from typing import List, Dict
from utils import get_critical_env_variable
from messagebroker_helper import MessageBrokerHelper

# Set up logger
logger = set_up_logger("cliclient")

# Global player name
player_name = None


async def main() -> None:
    # Define a function to handle the SIGINT signal
    def handle_sigint(signal, frame):
        asyncio.create_task(logout({"reason": "Ctrl-C"}))

    # Register the SIGINT handler
    signal.signal(signal.SIGINT, handle_sigint)

    # Get name from the player
    async def set_player_name() -> str:
        player_name = None
        while not player_name or " " in player_name:
            # Keep trying til they get the name right
            player_name = input("What do you want your name to be in this game?").strip(
                "."
            )
        # Subscribe to name-specific events
        await mbh.subscribe(f"game_update.{player_name}", game_update)
        await mbh.subscribe(f"logout.{player_name}", logout)
        await mbh.subscribe(f"instructions.{player_name}", instructions)
        await mbh.subscribe(f"room_update.{player_name}", room_update)
        # Publish name
        await mbh.publish("set_player_name", {"name": player_name, "role": "player"})
        return player_name

    # MBH event handlers

    # Game update event handler
    async def game_update(data: Dict) -> None:
        if data:
            logger.info(f"Received game update event: {data}")
            print(data)
        else:
            exit(logger, "Received empty game update event")

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

    # Player update event handler
    async def game_data_update(data: Dict) -> None:
        pass  # print("GAME UPDATE:", data)

    # Invalid name, try again
    async def name_invalid(data: Dict) -> None:
        logger.info(f"Invalid name event received: {data}")
        await mbh.unsubscribe(f"game_update.{player_name}")
        await mbh.unsubscribe(f"logout.{player_name}")
        await mbh.unsubscribe(f"instructions.{player_name}")
        await mbh.unsubscribe(f"room_update.{player_name}")

        player_name = set_player_name()
        await mbh.publish("set_player_name", {"name": player_name, "role": "player"})

    mbh = MessageBrokerHelper(
        get_critical_env_variable("GAMESERVER_HOSTNAME"),
        get_critical_env_variable("GAMESERVER_PORT"),
        {
            "set_player_name": {"mode": "publish"},
            "player_action": {"mode": "publish"},
            "game_update": {"mode": "subscribe", "callback": game_update},
            "instructions": {"mode": "subscribe", "callback": instructions},
            "shutdown": {"mode": "subscribe", "callback": shutdown},
            "logout": {"mode": "both", "callback": logout},
            "room_update": {"mode": "subscribe", "callback": room_update},
            "game_data_update": {"mode": "subscribe", "callback": game_data_update},
            "name_invalid": {"mode": "subscribe", "callback": name_invalid},
        },
    )

    # Start consuming messages
    await mbh.set_up_nats()

    player_name = await set_player_name()

    # Main loop
    while True:
        action = input("What do you want to do? ").strip()
        if action:
            await mbh.publish(
                "player_action", {"player_id": player_name, "player_input": action}
            )
        else:
            print("You must enter an action.")


# Main function to start the AI Broker
if __name__ == "__main__":
    asyncio.run(main())
