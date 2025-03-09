from gamemanager import GameManager
from storagemanager import StorageManager
from player import Player
from player_input_processor import PlayerInputProcessor
import asyncio
from os import environ
from messagebroker_helper import MessageBrokerHelper


async def run():

    def process_ai_response(data):
        print(f"Received AI response: {data}")

    mbh = MessageBrokerHelper(
        environ.get("GAMESERVER_HOSTNAME", "localhost"),
        environ.get("GAMESERVER_PORT", 4222),
        {
            "ai_request": {"mode": "publish"},
            "image_creation_request": {
                "mode": "subscribe",
                "callback": process_ai_response,
            },
        },
    )

    storage_manager = StorageManager()
    game_manager = GameManager(
        mbh=mbh,
        storage_manager=storage_manager,
        world_name="remotetest",
    )
    player = Player(game_manager.world, 0, "TestPlayer")

    print("Submitting remote request")
    await game_manager.ai_manager.submit_remote_request(
        player, "ai_request", "test prompt", "you are testing a remote request"
    )

    # Keep the connection alive
    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(run())
