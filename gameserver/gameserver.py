import socketio
import eventlet
import json
from datetime import datetime
import time


# Simple print alternative to flush everything for now
# TODO: logging, common utils
def log(message, second_message=""):
    print(str(message) + " " + second_message, flush=True)


log("Setting up SocketIO")
sio = socketio.Server(cors_allowed_origins="*")
app = socketio.WSGIApp(sio)


class Player:
    def __init__(self, sid, player_name):
        self.player_name = player_name
        self.current_room = "Living Room"
        self.sid = sid
        game_manager.register_player(sid, self)
        game_manager.update_player_room(self.sid, self.current_room)
        instructions = (
            f"Welcome to the game, {player_name}.\n{game_manager.commands_description}"
            + "Please input one of these commands."
        )
        for line in instructions.split("\n"):
            if line:
                game_manager.tell_player(self.sid, line, type="instructions")

        # Tell other players about this new player
        game_manager.tell_others(
            sid,
            f"{player_name} has joined the game; there are now {len(game_manager.games)} players.",
            shout=True,
        )

    def process_player_input(self, player_input):
        player_response = ""
        if player_input:
            words = str(player_input.lower()).split()
            command = words[0]
            # get the rest of the response apart from the first word
            rest_of_response = " ".join(words[1:])
            # strip out quotes from the outside of the response only
            if rest_of_response.startswith('"') and rest_of_response.endswith('"'):
                rest_of_response = rest_of_response[1:-1]
            # Do the same for single quotes
            elif rest_of_response.startswith("'") and rest_of_response.endswith("'"):
                rest_of_response = rest_of_response[1:-1]

            command = game_manager.synonyms.get(command, command)
            log(f"Command: {command}")
            if command in game_manager.rooms[self.current_room]["exits"]:
                player_response = self.move_player(command)
            elif command in game_manager.directions:
                player_response = "Sorry, you can't go that way."
            # TODO: this secret command shouldn't need to exist for causing all the other processes to end
            elif command == "xox":
                game_manager.shut_down(self.player_name)
            elif command == "say":
                log(f"User {self.player_name} says: {rest_of_response}")
                game_manager.tell_others(
                    self.sid, f'{self.player_name} says, "{rest_of_response}"'
                )
            elif command == "wait":
                time.sleep(10)
                player_response = "You decide to just wait a while."
                pass
            else:
                player_response = "Sorry, that is not a recognised command."
        else:
            player_response = "Sorry, you need to enter a command."
        return player_response

    def move_player(self, direction):
        # Set new room
        previous_room = self.current_room
        next_room = game_manager.rooms[self.current_room]["exits"][direction]

        # Check for other players you are leaving
        for other_player in game_manager.get_other_players(self.sid):
            if other_player.current_room == self.current_room:
                game_manager.tell_player(
                    other_player.sid,
                    f"{self.player_name} leaves, heading {direction} to the {next_room}.",
                )

        # Set new room
        self.current_room = next_room

        game_manager.update_player_room(self.sid, self.current_room)

        message = f"You went {direction} to {self.current_room}: {game_manager.get_room_description(self.current_room)}"

        # Check for other players you are arriving
        for other_player in game_manager.get_other_players(self.sid):
            if other_player.current_room == self.current_room:
                message += f" {other_player.player_name} is here."
                game_manager.tell_player(
                    other_player.sid,
                    f"{self.player_name} arrives from the {previous_room}.",
                )

        return message


class GameManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GameManager, cls).__new__(cls)
            cls._instance.games = {}
            # Set up game state
            cls._instance.rooms = cls._instance.get_rooms()
            # TODO: resolve this from the rooms document
            cls._instance.synonyms = {
                "n": "north",
                "e": "east",
                "s": "south",
                "w": "west",
            }
            cls._instance.directions = ["north", "east", "south", "west"]
            cls._instance.commands_description = "Available commands: " + ", ".join(
                cls._instance.directions
            )
            # append synyonyms to comamnds description explaining what each synonym means:
            cls._instance.commands_description += "\n"
            for key, value in cls._instance.synonyms.items():
                cls._instance.commands_description += f"{key} = {value}, "
            cls._instance.commands_description = cls._instance.commands_description[:-2]
            cls._instance.commands_description += "\n"
            # not xox
            cls._instance.commands_description += "wait = Do nothing for now.\n"
            cls._instance.commands_description += "say = say something to all other players in your current location, e.g. say which way shall we go?\n"

        return cls._instance

    def get_rooms(self):
        json_file_path = "map.json"
        with open(json_file_path, "r") as f:
            rooms = json.load(f)
        return rooms

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

    def update_player_room(self, sid, room):
        sio.emit("room_update", self.rooms[room]["image"], sid)

    def tell_everyone(self, message):
        if message.strip():
            sio.emit("game_update", message)

    def tell_others(self, sid, message, shout=False):
        if message.strip():
            for other_game_sid, other_game in game_manager.games.items():
                # Only tell another player if they are in the same room
                if sid != other_game_sid and (
                    shout
                    or other_game.current_room == game_manager.games[sid].current_room
                ):
                    sio.emit("game_update", message, other_game_sid)

    def tell_player(self, sid, message, type="game_update"):
        if message.strip():
            print("DEBUG: TELLING PLAYER:", sid, message)
            sio.emit(type, message, sid)

    def get_other_players(self, sid):
        other_players = []
        for other_game_sid, other_game in game_manager.games.items():
            if sid != other_game_sid:
                other_players.append(other_game)
        return other_players

    def shut_down(self, player_name):
        message = f"{player_name} has shut down the server."
        log(message)
        self.tell_everyone(message)
        # TODO: web client should do something when the back end is down, can we terminate the client too?
        # TODO: make this restart not die?
        sio.emit("shutdown", message)
        eventlet.sleep(1)
        exit()


@sio.event
def connect(sid, environ):
    log("Client connected:", sid)


@sio.event
def user_action(sid, player_input):
    player = game_manager.games[sid]
    log(f"Received user action: {player_input} from {sid}")
    player_response = player.process_player_input(player_input)
    # Respond to player
    if player_response:
        sio.emit("game_update", player_response, sid)


@sio.event
def set_player_name(sid, player_name):
    log(f"Received user name: {player_name} from {sid}")
    # Set up new game
    player = Player(sid, player_name)

    # TODO: this is a bit naff
    # Spawn the world-wide loop when the first player enters the game.
    if len(game_manager.games) == 1:
        eventlet.spawn(life_happens)

    # Tell this player where they are
    game_manager.tell_player(
        sid, game_manager.get_room_description(player.current_room)
    )


def life_happens():
    while True:
        # TODO: weather, time, life basically
        # currentTime = datetime.now().strftime("%H:%M:%S")
        # sio.emit("heartbeat", f"The time is now {currentTime}")
        eventlet.sleep(300)


if __name__ == "__main__":
    log("Starting up game server")
    game_manager = GameManager()
    eventlet.wsgi.server(eventlet.listen(("0.0.0.0", 3001)), app)
