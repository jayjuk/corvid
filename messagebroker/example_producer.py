# producer.py
import pika

# RabbitMQ connection parameters
connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
channel = connection.channel()

# Declare a queue (creates it if it doesn't exist)
channel.queue_declare(queue="test")

# Send a message
message = "Hello, RabbitMQ!"
channel.basic_publish(exchange="", routing_key="test", body=message)
print(f" [x] Sent '{message}'")

# Close the connection
connection.close()
