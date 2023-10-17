import socket
import socketio
import eventlet
import json
from datetime import datetime
import time
import sys


# Simple print alternative to flush everything for now
# TODO: logging, common utils
def log(message, second_message=""):
    print(str(message) + " " + second_message, flush=True)


log("Setting up SocketIO")
sio = socketio.Server(cors_allowed_origins="*")
app = socketio.WSGIApp(sio)


class Player:
    def __init__(self, game_server, sid, player_name):
        # Registering game server reference in player object to help with testing and minimise use of globals
        self.game_server = game_server
        self.last_action_time = time.time()
        self.player_name = player_name
        self.current_room = "Road"
        self.seen_rooms = {}
        self.sid = sid
        self.game_server.register_player(sid, self)
        self.game_server.update_player_room(self.sid, self.current_room)
        instructions = (
            f"Welcome to the game, {player_name}. "
            + self.game_server.get_players_text()
            + self.game_server.get_commands_description()
            + "Please input one of these commands."
        )
        for line in instructions.split("\n"):
            if line:
                self.game_server.tell_player(self.sid, line, type="instructions")

        # Tell this player where they are
        self.game_server.tell_player(
            sid, self.game_server.get_room_description(self.current_room)
        )
        self.seen_rooms[self.current_room] = True

        # Tell other players about this new player
        self.game_server.tell_others(
            sid,
            f"{player_name} has joined the game, starting in the {self.current_room}; there are now {self.game_server.get_player_count()} players.",
            shout=True,
        )
        self.game_server.emit_game_data_update()

    def process_player_input(self, player_input):
        self.last_action_time = time.time()
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

            command = self.game_server.synonyms.get(command, command)
            log(f"Command: {command}")

            # Call the function associated with a command
            if command in self.game_server.command_functions:
                player_response = self.game_server.command_functions[command](
                    self, rest_of_response
                )
            # Call the function associated with the command
            elif command in self.game_server.directions:
                player_response = self.move_player(command, rest_of_response)
            else:
                # Invalid command
                player_response = "Sorry, that is not a recognised command."
        else:
            # Empty command
            player_response = "Sorry, you need to enter a command."
        return player_response

    def move_player(self, direction, next_room=None):
        # Set new room
        previous_room = self.current_room
        if direction == "jump":
            # If next room specified, player has 'jumped'!
            departure_message_to_other_players = (
                f"{self.player_name} has disappeared in a puff of smoke!"
            )
            arrival_message_to_other_players = (
                f"{self.player_name} has materialised as if by magic!"
            )
        elif direction in self.game_server.rooms[self.current_room]["exits"]:
            next_room = self.game_server.rooms[self.current_room]["exits"][direction]

            departure_message_to_other_players = f"{self.player_name} leaves, heading {direction} to the {str(next_room).lower()}."
            arrival_message_to_other_players = (
                f"{self.player_name} arrives from the {previous_room.lower()}."
            )
        else:
            # Valid direction but no exit
            return "Sorry, you can't go that way."

        # Check for other players you are leaving
        for other_player in self.game_server.get_other_players(self.sid):
            if other_player.current_room == self.current_room:
                self.game_server.tell_player(
                    other_player.sid,
                    departure_message_to_other_players,
                )

        # Set new room
        self.current_room = next_room

        self.game_server.update_player_room(self.sid, self.current_room)

        if direction == "jump":
            action = "jumped"
        else:
            action = f"went {direction}"

        # Build message. only describe room if it is new to this player.
        message = f"You {action} to the {str(self.current_room).lower()}"
        if self.current_room in self.seen_rooms:
            message += f". {self.game_server.get_room_description(self.current_room, brief=True)}"
        else:
            message += f": {self.game_server.get_room_description(self.current_room)}"
            self.seen_rooms[self.current_room] = True

        # Check for other players you are arriving
        for other_player in self.game_server.get_other_players(self.sid):
            if other_player.current_room == self.current_room:
                message += f" {other_player.player_name} is here."
                self.game_server.tell_player(
                    other_player.sid,
                    arrival_message_to_other_players,
                )

        return message


class GameServer:
    _instance = None
    max_inactive_time = 300  # 5 minutes

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GameServer, cls).__new__(cls)
            cls._instance.players = {}
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

            # Define a dictionary to map commands to functions
            cls._instance.command_functions = {
                # TODO: limit this action to admins with the right permissions
                "look": cls._instance.do_look,
                "say": cls._instance.do_say,
                "wait": cls._instance.do_wait,
                "jump": cls._instance.do_jump,
                "💣": cls._instance.do_shutdown,
            }

            cls._instance.commands_description = (
                "Available commands: " + ", ".join(cls._instance.directions) + ". "
            )
            # append synyonyms to comamnds description explaining what each synonym means:
            cls._instance.commands_description += "\n"
            for key, value in cls._instance.synonyms.items():
                cls._instance.commands_description += f"{key} = {value}, "
            cls._instance.commands_description = cls._instance.commands_description[:-2]
            cls._instance.commands_description += "\n"
            # not xox
            cls._instance.commands_description += "wait = Do nothing for now.\n"
            cls._instance.commands_description += (
                "look = Get a description of your current location.\n"
            )
            cls._instance.commands_description += "say = say something to all other players in your current location, e.g. say which way shall we go?\n"

        return cls._instance

    # All these 'do_' functions are for processing commands from the player.
    # They all take the player object and the rest of the response as arguments,
    # Even if they're not needed. This is to keep the command processing simple.

    def do_look(self, player, rest_of_response):
        # Not used, next line is to avoid warnings
        f"""{player.player_name}  {rest_of_response}"""
        return f"You look again at the {str(player.current_room).lower()}: {self.get_room_description(player.current_room)}"

    def do_say(self, player, rest_of_response):
        log(f"User {player.player_name} says: {rest_of_response}")
        if self.get_player_count() == 1:
            player_response = "You are the only player in the game currently!"
        else:
            told_count = self.tell_others(
                player.sid, f'{player.player_name} says, "{rest_of_response}"'
            )
            if told_count == 0:
                player_response = "There is no one else here to hear you!"
            else:
                player_response = f"You say, '{rest_of_response}'."
        return player_response

    def do_wait(self, player, rest_of_response):
        # Not used, next line is to avoid warnings
        f"""{player.player_name}  {rest_of_response}"""
        return "You decide to just wait a while."

    def do_jump(self, player, rest_of_response):
        # Jump to location of another player named in rest_of_response
        other_player_name = rest_of_response
        # find location of other player
        other_player_location = self.get_player_location_by_name(
            player.sid, other_player_name
        )
        # if found, move player there
        if other_player_location:
            return player.move_player("jump", other_player_location)
        else:
            return f"Sorry, '{other_player_name}' is not a valid player name."

    def do_shutdown(self, player, rest_of_response):
        message = f"{player.player_name} has shut down the server, saying '{rest_of_response}'."
        log(message)
        self.tell_everyone(message)
        # TODO: web client should do something when the back end is down, can we terminate the client too?
        # TODO: make this restart not die?
        sio.emit("shutdown", message)
        eventlet.sleep(1)
        sys.exit(1)

    # End of 'do_' functions

    def get_commands_description(self):
        return self.commands_description

    def get_players_text(self):
        if self.get_player_count() == 1:
            return "You are the first player to join the game.\n"
        else:
            return f"There are {self.get_player_count()} players online already.\n"

    def get_player_location_by_name(self, sid, player_name):
        for other_player in self.get_other_players(sid):
            if str(other_player.player_name).lower() == str(player_name).lower():
                return other_player.current_room
        return None

    def get_player_count(self):
        return len(self.players)

    def get_rooms(self):
        json_file_path = "map.json"
        with open(json_file_path, "r") as f:
            rooms = json.load(f)
        return rooms

    def register_player(self, sid, game):
        self.players[sid] = game
        return game

    def get_room_description(self, room, brief=False):
        if brief:
            description = ""
        else:
            description = self.rooms[room]["description"]
        # Always describe exits
        description += " Available exits: "
        for exit in self.rooms[room]["exits"]:
            description += exit + ": " + self.rooms[room]["exits"][exit] + ".  "
        return description

    def update_player_room(self, sid, room):
        sio.emit("room_update", self.rooms[room]["image"], sid)

    def tell_everyone(self, message):
        if message.strip():
            sio.emit("game_update", message)

    def tell_others(self, sid, message, shout=False):
        told_count = 0
        if message.strip():
            for other_game_sid, other_game in self.players.items():
                # Only tell another player if they are in the same room
                if sid != other_game_sid and (
                    shout or other_game.current_room == self.players[sid].current_room
                ):
                    sio.emit("game_update", message, other_game_sid)
                    told_count += 1
        return told_count

    def tell_player(self, sid, message, type="game_update"):
        if message.strip():
            sio.emit(type, message, sid)

    def get_other_players(self, sid):
        other_players = []
        for other_game_sid, other_game in self.players.items():
            if sid != other_game_sid:
                other_players.append(other_game)
        return other_players

    def emit_game_data_update(self):
        game_data = {"player_count": self.get_player_count()}
        sio.emit(
            "game_data_update",
            game_data,
        )

    def check_players_activity(self):
        current_time = time.time()
        sids_to_remove = []
        # First go through players and make a list of who to remove
        for player_sid, player in self.players.items():
            if current_time - player.last_action_time > self.max_inactive_time:
                sids_to_remove.append(player_sid)
        # Then once you're out of that dictionary, remove them
        for player_sid in sids_to_remove:
            self.remove_player(
                player_sid, "You have been logged out due to inactivity."
            )

    def remove_player(self, sid, reason):
        player = self.players[sid]
        self.tell_player(
            player.sid,
            reason,
        )
        self.tell_others(
            sid,
            f"{player.player_name} has left the game; there are now {self.get_player_count()} players.",
            shout=True,
        )
        self.emit_game_data_update()
        del self.players[sid]

    def game_metadata_update(self):
        while True:
            # TODO: time out players who leave
            self.check_players_activity()

            # For now, the only thing happening is broadcast of player count
            # So that AI players can pause when there are no human players, saving money
            self.emit_game_data_update()

            # TODO: think about whether to do this when players join/leave instead,
            # and use this loop for other stuff in the game later
            eventlet.sleep(60)


# Event handlers
# These use global game_server


@sio.event
def connect(sid, environ):
    log("Client connected:", sid)


@sio.event
def user_action(sid, player_input):
    player = game_server.players[sid]
    log(f"Received user action: {player_input} from {sid}")
    player_response = player.process_player_input(player_input)
    # Respond to player
    if player_response:
        sio.emit("game_update", player_response, sid)


@sio.event
def set_player_name(sid, player_name):
    log(f"Received user name: {player_name} from {sid}")
    # Set up new game
    player = Player(game_server, sid, player_name)

    # TODO: this is a bit naff
    # Spawn the world-wide metadata loop when the first player enters the game.
    if game_server.get_player_count() == 1:
        eventlet.spawn(game_server.game_metadata_update)


# End of event handlers


if __name__ == "__main__":
    hostname = socket.getfqdn()
    if hostname.endswith(".lan"):
        hostname = hostname[:-4]
    log(f"Starting up game server on {hostname}")
    game_server = GameServer()
    eventlet.wsgi.server(eventlet.listen(("0.0.0.0", 3001)), app)
