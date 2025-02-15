from typing import Dict, Any
from os import environ
import socket
import socketio
import eventlet
import json

# Set up logger before importing other own modules
from utils import setup_logger

logger = setup_logger("Message Broker", sio=None)

from messagebroker_helper import MessageBrokerHelper

logger.info("Setting up SocketIO")
sio = socketio.Server(cors_allowed_origins="*")
app = socketio.WSGIApp(sio)

# Event handlers


# Connection
@sio.event
def connect(sid: str, environ: Dict[str, Any]) -> None:
    logger.info(f"Client connected: {sid}")


# Player setup
@sio.event
def set_player_name(sid: str, player_info: Dict[str, str]) -> None:
    logger.info(
        f"Client requesting player setup: {sid}, {player_info.get('name')}, {player_info.get('role')}"
    )
    player_sid = player_info.get("player_sid")
    logger.info(f"Player SID: {player_sid}")
    logger.info(f"Native SID: {sid}")
    mbh.publish("set_player_name", {"sid": player_sid, "player_info": player_info})


@sio.event
def user_action(sid: str, player_input: str):
    logger.info(f"Client requesting user action: {sid}, {player_input}")
    mbh.publish("user_action", {"sid": sid, "player_input": player_input})


# Disconnection
@sio.event
def disconnect(sid: str) -> None:
    logger.info(f"Client disconnected: {sid}")
    mbh.publish("user_disconnect", {"sid": sid})


# End of event handlers


def client_message(body):
    logger.info(f"Received client message: {body}")
    data = body  # json.loads(body)
    event_name = data.get("event_name", "")
    data = data.get("data", {})
    if data:
        sid = data.get("sid", None)
        if event_name and data:
            if sid:
                logger.info(f"Emitting event {event_name} to {sid}, data: {data}")
                sio.emit(event_name, data, sid)
            else:
                logger.info(f"Emitting event {event_name} to all, data: {data}")
                sio.emit(event_name, data)
        else:
            logger.error("No event name in client message")
    else:
        logger.error("No data in client message")


if __name__ == "__main__":
    hostname: str = socket.getfqdn()
    if hostname.endswith(".lan"):
        hostname = hostname[:-4]
    # TODO #65 Do not allow default port, and make this common
    port: int = int(environ.get("GAMESERVER_PORT", "3001"))

    # Set up the message broker
    logger.info(
        f"Setting up message broker on hostname {hostname} port {port} - republishes incoming SocketIO events to RabbitMQ"
    )
    mbh = MessageBrokerHelper(
        hostname,
        {
            "set_player_name": {"mode": "publish"},
            "user_action": {"mode": "publish"},
            "user_disconnect": {"mode": "publish"},
            # Subscribe to client_message events
            "client_message": {
                "mode": "subscribe",
                "callback": client_message,
            },
        },
        use_threading=True,
    )
    logger.info("Message broker set up")

    # Launch the WSGI server for the SocketIO app
    logger.info(f"Launching WSGI server on {hostname}:{port}")

    # Start consuming messages
    mbh.start_consuming()

    # Start the WSGI server
    logger.info("Starting WSGI server")
    eventlet.wsgi.server(eventlet.listen(("0.0.0.0", port)), app)
