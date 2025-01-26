from typing import Dict, List, Any
import pika
import threading
import json

# Set up logger
from logger import setup_logger

logger = setup_logger("Message Broker Helper", sio=None)


class MessageBrokerHelper:
    """Simplify exchanging messages with other back-end services."""

    # Constructor
    def __init__(
        self, host: str, queue_map: List[Dict[str, Any]], use_threading: bool = False
    ):

        # RabbitMQ connection parameters
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host or "localhost")
        )
        self.channel = connection.channel()
        self.callback_functions = {}
        self.publisher_queues = {}

        am_consumer: bool = False
        startup_messages: list = []
        for queue_name, queue_properties in queue_map.items():
            # Declare a queue (creates it if it doesn't exist
            self.channel.queue_declare(queue=queue_name)
            # Store the callback function
            self.callback_functions[queue_name] = queue_properties.get("callback", None)
            # Depending on the mode, either register publisher or subscriber
            if queue_properties.get("mode", "") == "publish":
                self.publisher_queues[queue_name] = True
                if queue_properties.get("startup", False):
                    startup_messages.append(
                        (queue_name, queue_properties.get("startup_message", ""))
                    )
            elif queue_properties.get("mode", "") == "subscribe":
                am_consumer = True
                logger.info(f"Subscribing to queue {queue_name}")
                # Subscribe to the queue
                self.channel.basic_consume(
                    queue=queue_name,
                    on_message_callback=self.global_callback,
                    auto_ack=True,
                )

        # Publish startup messages
        for queue_name, message in startup_messages:
            self.publish(queue_name, message)

        if am_consumer:
            if use_threading:
                logger.info("Registering as message consumer in background thread.")
                # Start a new thread to consume messages
                self.consumer_thread = threading.Thread(
                    target=self.channel.start_consuming
                )
                self.consumer_thread.start()
            else:
                logger.info("Registering as message consumer.")
                # Start consuming messages
                self.channel.start_consuming()

    # Global callback function
    def global_callback(self, ch, method, properties, body):
        queue_name = method.routing_key
        callback = self.callback_functions.get(queue_name, None)
        logger.info(f"Received message: {body.decode()}")
        # Call specific game manager callback function
        if callback:
            # Check if the body contains JSON and should be a dictionary
            try:
                body_dict: dict = json.loads(body.decode())
                callback(body_dict)
            except json.JSONDecodeError:
                callback(body.decode())
        else:
            logger.warning(f"No callback function for queue {queue_name}")

    # Send a message
    def publish(self, queue: str, message: Any):
        # First check the queue was registered upfront as a publisher
        if queue not in self.publisher_queues:
            logger.error(f"Queue {queue} not registered as a publisher")
            return

        if isinstance(message, dict):
            message = json.dumps(message)
        elif not isinstance(message, str):
            raise ValueError("Message must be a dictionary or a string")

        self.channel.basic_publish(exchange="", routing_key=queue, body=message)

        logger.info(f"Sent message to queue {queue}: {message}")
