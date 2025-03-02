from os import environ
import asyncio
from utils import get_critical_env_variable
from messagebroker_helper import MessageBrokerHelper

if __name__ == "__main__":

    mbh = MessageBrokerHelper(
        get_critical_env_variable("GAMESERVER_HOSTNAME"),
        get_critical_env_variable("GAMESERVER_PORT"),
        {
            "shutdown": {"mode": "publish"},
        },
    )
    print("Message broker set up")
    # Now shut down
    asyncio.run(mbh.set_up_nats())
    asyncio.run(mbh.publish("shutdown", "shutdown"))
    print("Published shutdown message.")

# This is a simple script that sends a shutdown message to the message broker. It is used to shut down the game server.
