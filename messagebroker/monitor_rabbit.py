import pika
import time

# Implement simple program to output all messages without any processing or consuming them

# RabbitMQ connection parameters
try:
    connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    channel = connection.channel()
except pika.exceptions.AMQPConnectionError as e:
    print(f"Failed to connect to RabbitMQ: {e}")
    exit(1)

queues = [
    # "ai_request",
    # "ai_response",
    "set_player_name",
    "client_message",
    # "user_action",
    # "user_disconnect",
]

while True:
    for queue in queues:
        # print(f"Checking queue {queue}")
        method_frame, header_frame, body = channel.basic_get(
            queue=queue, auto_ack=False
        )
        if method_frame:
            print(f"\n\nReceived message from {queue}: {body}\n\n")
    time.sleep(1)  # Sleep for a while before checking again
