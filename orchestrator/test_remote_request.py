from worldmanager import worldmanager
from storagemanager import StorageManager
from person import Person
from user_input_processor import UserInputProcessor
import asyncio
from os import environ
from messagebroker_helper import MessageBrokerHelper


async def run():

    def process_ai_response(data):
        print(f"Received AI response: {data}")

    mbh = MessageBrokerHelper(
        environ.get("ORCHESTRATOR_HOSTNAME", "localhost"),
        environ.get("ORCHESTRATOR_PORT", 4222),
        {
            "ai_request": {"mode": "publish"},
            "image_creation_request": {
                "mode": "subscribe",
                "callback": process_ai_response,
            },
        },
    )

    storage_manager = StorageManager()
    world_manager = worldmanager(
        mbh=mbh,
        storage_manager=storage_manager,
        world_name="remotetest",
    )
    person = Person(world_manager.world, 0, "TestPerson")

    print("Submitting remote request")
    await world_manager.ai_manager.submit_remote_request(
        person, "ai_request", "test prompt", "you are testing a remote request"
    )

    # Keep the connection alive
    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(run())
