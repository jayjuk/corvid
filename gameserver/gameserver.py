import socketio
import eventlet
import json
from datetime import datetime


# Simple print alternative to flush everything for now
def log(message, second_message=""):
    print(str(message) + " " + second_message, flush=True)


log("Setting up SocketIO")
sio = socketio.Server(cors_allowed_origins="*")
app = socketio.WSGIApp(sio)

# TODO: this is global
global rooms
global player_room
player_room = {}


class Player:
    def __init__(self, sid, player_name):
        self.player_name = player_name
        self.current_room = "Living Room"
        self.sid = sid
        game_manager.register_player(sid, self)
        game_manager.tell_player(self.sid, f"Welcome to the game, {player_name}.")
        game_manager.tell_others(self.sid, f"{player_name} has joined.")

    def process_player_input(self, player_input):
        player_response = ""
        words = str(player_input.lower()).split()
        command = words[0]
        command = game_manager.synonyms.get(command, command)
        log(f"Command: {command}")
        if command in game_manager.rooms[self.current_room]["exits"]:
            player_response = self.move_player(command)
        elif command in game_manager.directions:
            player_response = "Sorry, you can't go that way."
        elif command == "xxxdie":
            log("Server shutdown initiated.")
            game_manager.tell_everyone(f"{self.player_name} has shut down the server.")
            eventlet.sleep(1)
            exit()
        else:
            log(f"User {self.player_name} spoke, I assume: {player_input}")
            game_manager.tell_others(
                self.sid, f'{self.player_name} shouts, "{player_input}"'
            )
        return player_response

    def move_player(self, direction):
        # Check for other players you are leaving
        for other_player in game_manager.get_other_players(self.sid):
            if other_player.current_room == self.current_room:
                game_manager.tell_player(
                    other_player.sid, f"{self.player_name} leaves."
                )

        # Set new room
        self.current_room = game_manager.rooms[self.current_room]["exits"][direction]

        message = f"You went {direction} to {self.current_room}: {game_manager.get_room_description(self.current_room)}"

        # Check for other players you are arriving
        for other_player in game_manager.get_other_players(self.sid):
            if other_player.current_room == self.current_room:
                message += f" {other_player.player_name} is here."
                game_manager.tell_player(
                    other_player.sid, f"{self.player_name} arrives."
                )

        return message


class GameManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GameManager, cls).__new__(cls)
            cls._instance.games = {}
            # Set up game state
            cls._instance.rooms = get_rooms()
            # TODO: resolve this from the rooms document
            cls._instance.synonyms = {
                "n": "north",
                "e": "east",
                "s": "south",
                "w": "west",
            }
            cls._instance.directions = ["north", "east", "south", "west"]

        return cls._instance

    def register_player(self, sid, game):
        self.games[sid] = game
        return game

    def get_room_description(self, room):
        description = (
            f"You are in {room}: {self.rooms[room]['description']} Available exits: "
        )
        for exit in self.rooms[room]["exits"]:
            description += exit + ": " + self.rooms[room]["exits"][exit] + ".  "
        return description

    def tell_everyone(self, message):
        sio.emit("game_update", message)

    def tell_others(self, sid, message):
        for other_game_sid in game_manager.games:
            if sid != other_game_sid:
                sio.emit("game_update", message, other_game_sid)

    def tell_player(self, sid, message):
        sio.emit("game_update", message, sid)

    def get_other_players(self, sid):
        other_players = []
        for other_game_sid, other_game in game_manager.games.items():
            if sid != other_game_sid:
                other_players.append(other_game)
        return other_players


def get_rooms():
    json_file_path = "map.json"
    with open(json_file_path, "r") as f:
        rooms = json.load(f)
    return rooms


@sio.event
def connect(sid, environ):
    log("Client connected:", sid)


@sio.event
def user_action(sid, player_input):
    player = game_manager.games[sid]
    log(f"Received user action: {player_input} from {sid}")
    player_response = player.process_player_input(player_input)
    # Respond to player
    sio.emit("game_update", player_response, sid)


@sio.event
def set_player_name(sid, player_name):
    log(f"Received user name: {player_name} from {sid}")
    # Set up new game
    player = Player(sid, player_name)
    # Tell other players about this new player
    player_count = len(game_manager.games)
    game_manager.tell_others(
        sid,
        f"A player has joined. There are now {player_count} players in the game.",
    )
    # TODO: this is a bit naff
    # Spawn the world-wide loop when the first player enters the game.
    if player_count == 1:
        eventlet.spawn(life_happens)

    # Tell this player where they are
    game_manager.tell_player(
        sid, game_manager.get_room_description(player.current_room)
    )


def life_happens():
    while True:
        # weather, time, life basically
        currentTime = datetime.now().strftime("%H:%M:%S")
        sio.emit("game_update", f"The time is now {currentTime}")
        eventlet.sleep(300)


if __name__ == "__main__":
    log("Start of main")
    game_manager = GameManager()

    # host_name = "localhost"  # "0.0.0.0"
    host_name = "0.0.0.0"
    log("Last thing before I set up the WSGI server")
    eventlet.wsgi.server(eventlet.listen((host_name, 3001)), app)
