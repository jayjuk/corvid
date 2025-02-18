import asyncio
import json
from nats.aio.client import Client as NATS
from nats.aio.errors import ErrConnectionClosed, ErrTimeout, ErrNoServers
from logger import setup_logger, exit

logger = setup_logger("Message Broker Helper", sio=None)


class MessageBrokerHelper:
    """Simplify exchanging messages with other back-end services."""

    def __init__(self, host: str, queue_map: dict):
        self.host = host or "localhost"
        self.queue_map = queue_map
        self.callback_functions = {}

        self.nc = NATS()
        self.publisher_queues = {}
        self.am_consumer = False
        self.startup_messages = []

        for queue_name, queue_properties in queue_map.items():
            if queue_properties.get("mode", "") == "publish":
                self.publisher_queues[queue_name] = True
                if queue_properties.get("startup", False):
                    self.startup_messages.append(
                        (queue_name, queue_properties.get("startup_message", ""))
                    )
            elif queue_properties.get("mode", "") == "subscribe":
                self.am_consumer = True
                self.callback_functions[queue_name] = queue_properties.get(
                    "callback", None
                )
                logger.info(f"Subscribing to queue {queue_name}")

    async def setup_nats(self):
        try:
            await self.nc.connect(servers=[f"nats://{self.host}:4222"])
            logger.info(f"Connected to NATS server at {self.host}")

            # Publish startup messages
            for queue_name, message in self.startup_messages:
                await self.publish(queue_name, message)

            if self.am_consumer:
                await self.start_consuming()

        except ErrNoServers as e:
            logger.error(f"Could not connect to NATS server: {e}")

    async def start_consuming(self):
        if self.am_consumer:
            for queue_name in self.callback_functions.keys():
                await self.nc.subscribe(queue_name, cb=self.global_callback)
                logger.info(f"Subscribed to queue {queue_name}")

    async def global_callback(self, msg):
        """Handles received messages."""
        logger.info(f"Received message: {msg.subject}")
        queue_name = msg.subject
        callback = self.callback_functions.get(queue_name, None)
        # Check callback is a function
        if not callable(callback):
            exit(logger, f"Callback function for queue {queue_name} is not callable")

        body = msg.data.decode()
        logger.info(f"Received message: {body}")

        if callback:
            # Convert to dictionary if possible
            try:
                body_dict = json.loads(body)
                if isinstance(body_dict, dict):
                    await callback(body_dict)
                else:
                    logger.warning(
                        f"Message not a dictionary: {body}, passing to callback function as string"
                    )
                    await callback(body)
            except json.JSONDecodeError:
                await callback(body)
        else:
            logger.warning(f"No callback function for queue {queue_name}")

    async def publish(self, queue: str, message: any, player_id: str = None):
        """Publish a message to a queue."""
        if queue not in self.publisher_queues:
            logger.error(f"Queue {queue} not registered as a publisher")
            return

        if isinstance(message, dict):
            message = json.dumps(message)
        elif not isinstance(message, str):
            exit(
                logger,
                f"Message must be a dictionary or a string. Message {message} is of type: {type(message)}",
            )

        if player_id:
            # Add player ID to queue
            queue = f"{queue}.{player_id}"

        await self.nc.publish(queue, message.encode())
        logger.info(f"Sent message to queue {queue}: {message}")

    def close(self):
        """Close the NATS connection."""
        if self.nc.is_connected:
            asyncio.run(self.nc.close())
            logger.info("Closed NATS connection")
