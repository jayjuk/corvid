import asyncio
import json
from nats.aio.client import Client as NATS
from nats.aio.errors import ErrConnectionClosed, ErrTimeout, ErrNoServers
from logger import set_up_logger, exit

logger = set_up_logger("Message Broker Helper")


class MessageBrokerHelper:
    """Simplify exchanging messages with other back-end services."""

    def __init__(self, host: str, port: int, queue_map: dict):
        """Initialise the MessageBrokerHelper."""
        self.host = host or "localhost"
        self.port = port or 4222
        self.queue_map = queue_map
        self.callback_functions = {}

        self.nc = NATS()
        self.publisher_queues = {}
        self.am_consumer = False
        self.startup_messages = []

        for queue_name, queue_properties in queue_map.items():
            if queue_properties.get("mode", "") in ("publish", "both"):
                self.publisher_queues[queue_name] = True
                if queue_properties.get("startup", False):
                    self.startup_messages.append(
                        (queue_name, queue_properties.get("startup_message", ""))
                    )
            if queue_properties.get("mode", "") in ("subscribe", "both"):
                self.am_consumer = True
                # Set up callback functions, do not actually subscribe yet
                self.callback_functions[queue_name] = queue_properties.get(
                    "callback", None
                )

    async def set_up_nats(self):
        try:
            await self.nc.connect(servers=[f"nats://{self.host}:{self.port}"])
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

    async def subscribe(self, queue_name: str, callback):
        """Subscribe to a queue and set the callback function."""
        if (
            queue_name not in self.callback_functions
            and queue_name.split(".")[0] not in self.callback_functions
        ):
            logger.error(
                f"Queue {queue_name} or {queue_name.split('.')[0]} not registered as a subscriber"
            )
            return

        self.callback_functions[queue_name] = callback
        await self.nc.subscribe(queue_name, cb=self.global_callback)
        logger.info(f"Subscribed to queue {queue_name}")

    async def unsubscribe(self, queue_name: str):
        await self.nc.unsubscribe(queue_name)
        logger.info(f"Unsubscribed from queue {queue_name}")

    async def global_callback(self, msg):
        """Handles received messages."""
        body = msg.data.decode()
        logger.info(f"Global callback invoked for message with subject: {msg.subject}")
        logger.info(f"Message body: <{body}>")
        callback = self.callback_functions.get(msg.subject, None)
        # Check callback is a function
        if not callback:
            exit(logger, f"No callback function for queue {msg.subject}")
        elif not callable(callback):
            exit(logger, f"Callback function for queue {msg.subject} is not callable")

        # Display callback function name
        logger.info(f"Invoking callback function: {callback.__name__}...")

        # Convert body to dictionary if possible
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
            if ("{" in body and "}" in body) or ("[" in body and "]" in body):
                logger.warning(f"JSONDecodeError: {body}")
            # If message is not JSON, this is normal (simple message), pass it to the callback function as a string
            await callback(body)

    async def publish(self, queue: str, message: any, user_id: str = None):
        """Publish a message to a queue."""
        if not message:
            exit(logger, "Message is empty")

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

        if user_id:
            # Add user ID to queue
            queue = f"{queue}.{user_id.lower()}"

        await self.nc.publish(queue, message.encode())
        await self.nc.flush()
        logger.info(f"Sent message to queue {queue}: {message}")

    def close(self):
        """Close the NATS connection."""
        if self.nc.is_connected:
            asyncio.run(self.nc.close())
            logger.info("Closed NATS connection")
