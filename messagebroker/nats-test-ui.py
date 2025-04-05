import asyncio
from nats.aio.client import Client as NATS


async def publish_messages():
    nc = NATS()

    await nc.connect("localhost:4222")

    # Publish a message to the "instructions" subject
    await nc.publish("instructions", b"This is an instruction message")

    # Publish a world update message to the "world_update" subject
    await nc.publish("world_update", b'{"data": "This is a world update"}')

    # Publish a room update message to the "room_update" subject
    await nc.publish(
        "room_update",
        b'{"image": "http://example.com/image.png", "title": "Room Title", "description": "Room Description", "exits": "north, south"}',
    )

    # Publish a shutdown message to the "shutdown" subject
    await nc.publish("shutdown", b"The server is shutting down!")

    # Publish a logout message to the "logout" subject
    await nc.publish("logout", b"You have been logged out!")

    # Publish a name invalid message to the "name_invalid" subject
    await nc.publish("name_invalid", b"The player name is invalid!")

    await nc.drain()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(publish_messages())
