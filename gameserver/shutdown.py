from os import environ
import asyncio
from messagebroker_helper import MessageBrokerHelper

if __name__ == "__main__":

    mbh = MessageBrokerHelper(
        environ.get("GAMESERVER_HOSTNAME", "localhost"),
        {
            "shutdown": {"mode": "publish"},
        },
    )
    print("Message broker set up")
    # Now shut down
    asyncio.run(mbh.set_up_nats())
    asyncio.run(mbh.publish("shutdown", "shutdown"))
    print("Shutting down")
    exit(0)

# This is a simple script that sends a shutdown message to the message broker. It is used to shut down the game server.
