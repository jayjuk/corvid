# consumer.py
import pika

# RabbitMQ connection parameters
connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
channel = connection.channel()

queue_name = "ai_request"
# Declare the same queue (creates it if it doesn't exist)
channel.queue_declare(queue=queue_name)


# Define a callback function to process messages
def callback(ch, method, properties, body):
    print(f" [x] Received '{body.decode()}'")


# Subscribe to the queue
channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)

print(" [*] Waiting for messages. To exit press CTRL+C")
channel.start_consuming()
