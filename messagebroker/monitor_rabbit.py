import pika
import time

# Implement simple program to output all messages without any processing or consuming them

# RabbitMQ connection parameters
try:
    connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    channel = connection.channel()
except pika.exceptions.AMQPConnectionError as e:
    print(f"Failed to connect to RabbitMQ: {e}")


def callback(ch, method, properties, body):
    print(f"\n\nReceived message: {body}\n\n")


queues = ["ai_request", "ai_response"]

for queue in queues:
    channel.queue_declare(queue=queue, passive=True)
    channel.basic_get(queue=queue, on_message_callback=callback, auto_ack=False)

try:
    print("Waiting for messages. To exit press CTRL+C")
    channel.start_consuming()
except KeyboardInterrupt:
    print("Interrupted by user")
finally:
    connection.close()
