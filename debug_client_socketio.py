import socketio

sio = socketio.Client()


@sio.on("*")
def catch_all(event, data):
    print(f"Received event '{event}': {data}")


@sio.event
def connect():
    print("Connected to Server.")


@sio.event
def disconnect():
    print("Disconnected from Server.")


def main():
    sio.connect(
        "http://localhost:3001"
    )  # adjust this to your server's address and port
    try:
        sio.wait()
    except KeyboardInterrupt:
        print("\nExiting...")
        sio.disconnect()


if __name__ == "__main__":
    main()
