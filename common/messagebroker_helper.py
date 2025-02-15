import pika
import threading
import json
from logger import setup_logger

logger = setup_logger("Message Broker Helper", sio=None)


class MessageBrokerHelper:
    """Simplify exchanging messages with other back-end services."""

    def __init__(self, host: str, queue_map: dict, use_threading: bool = False):
        self.host = host or "localhost"
        self.queue_map = queue_map
        self.callback_functions = {}
        self.use_threading = use_threading

        # Create a separate connection & channel for publishing
        logger.info(f"Setting up message broker for host {self.host}")
        self.publish_connection = pika.BlockingConnection(
            pika.ConnectionParameters(self.host)
        )
        self.publish_channel = self.publish_connection.channel()

        self.publisher_queues = {}

        self.am_consumer = False
        startup_messages = []

        for queue_name, queue_properties in queue_map.items():
            # Declare a queue for publishing
            self.publish_channel.queue_declare(queue=queue_name)

            if queue_properties.get("mode", "") == "publish":
                self.publisher_queues[queue_name] = True
                if queue_properties.get("startup", False):
                    startup_messages.append(
                        (queue_name, queue_properties.get("startup_message", ""))
                    )
            elif queue_properties.get("mode", "") == "subscribe":
                self.am_consumer = True
                self.callback_functions[queue_name] = queue_properties.get(
                    "callback", None
                )
                logger.info(f"Subscribing to queue {queue_name}")

        # Publish startup messages
        for queue_name, message in startup_messages:
            self.publish(queue_name, message)

    def start_consuming(self):
        if self.am_consumer:
            if self.use_threading:
                logger.info("Registering as message consumer in background thread.")
                self.use_threading = True
                self.consumer_thread = threading.Thread(
                    target=self.consumer_thread_func, daemon=True
                )
                self.consumer_thread.start()
            else:
                logger.info("Registering as message consumer.")
                self.consumer_thread_func()  # Run in main thread if no threading

    def consumer_thread_func(self):
        logger.info("Starting messaging consumer thread.")
        """Runs the consumer """
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(self.host))
        self.channel = self.connection.channel()

        # Declare queues for consumption
        for queue_name in self.callback_functions.keys():
            self.channel.queue_declare(queue=queue_name)
            self.channel.basic_consume(
                queue=queue_name,
                on_message_callback=self.global_callback,
                auto_ack=True,
            )

        logger.info("RabbitMQ Consumer Thread: Waiting for messages...")
        self.channel.start_consuming()

    def check_for_messages(self):
        self.channel.process_data_events()

    def global_callback(self, ch, method, properties, body):
        """Handles received messages."""
        queue_name = method.routing_key
        callback = self.callback_functions.get(queue_name, None)
        logger.info(f"Received message: {body.decode()}")

        if callback:
            try:
                body_dict = json.loads(body.decode())
                callback(body_dict)
            except json.JSONDecodeError:
                callback(body.decode())
        else:
            logger.warning(f"No callback function for queue {queue_name}")

    def emit(self, event_name: str, data: any, sid: str = None):
        """Emit a client message to a sid."""
        if not isinstance(data, dict):
            data = {"data": data}
        data["sid"] = sid
        self.publish("client_message", {"event_name": event_name, "data": data})

    def publish(self, queue: str, message: any):
        """Publish a message to a queue."""
        if queue not in self.publisher_queues:
            logger.error(f"Queue {queue} not registered as a publisher")
            return

        if isinstance(message, dict):
            message = json.dumps(message)
        elif not isinstance(message, str):
            raise ValueError("Message must be a dictionary or a string")

        self.publish_channel.basic_publish(exchange="", routing_key=queue, body=message)
        logger.info(f"Sent message to queue {queue}: {message}")
