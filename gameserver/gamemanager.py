import os
import eventlet
import time
import sys
from player import Player
from world import World
from logger import setup_logger

# Set up logging
logger = setup_logger()


class GameManager:
    _instance = None

    def __new__(cls, sio):
        if cls._instance is None:
            cls._instance = super(GameManager, cls).__new__(cls)

            # Static variables
            cls._instance.max_inactive_time = 300  # 5 minutes
            cls._instance.background_loop_active = False

            # Set up game state
            cls._instance.sio = sio
            cls._instance.players = {}
            cls._instance.player_sid_to_name_map = {}
            cls._instance.world = World()

            # TODO: resolve this from the rooms document
            cls._instance.synonyms = {
                "n": "north",
                "e": "east",
                "s": "south",
                "w": "west",
                "exit": "quit",
                "pick": "get",
                "inv": "inventory",
            }
            cls._instance.directions = ["north", "east", "south", "west"]

            # Define a dictionary to map commands to functions
            cls._instance.command_functions = {
                # TODO: limit this action to admins with the right permissions
                "look": {
                    "function": cls._instance.do_look,
                    "description": "Get a description of your current location",
                },
                "say": {
                    "function": cls._instance.do_say,
                    "description": "Say something to all other players in your *current* location, e.g. say which way shall we go?",
                },
                "shout": {
                    "function": cls._instance.do_shout,
                    "description": "Shout something to everyone in the game, e.g. shout Where is everyone?",
                },
                "wait": {
                    "function": cls._instance.do_wait,
                    "description": "Do nothing for now",
                },
                "jump": {
                    "function": cls._instance.do_jump,
                    "description": "Jump to location of another player named in rest_of_response",
                },
                "quit": {
                    "function": cls._instance.do_quit,
                    "description": "",  # Don't encourage the AI to quit! TODO: make this only appear in the help to human players
                },
                "get": {
                    "function": cls._instance.do_get,
                    "description": "Pick up an object in your current location",
                },
                "drop": {
                    "function": cls._instance.do_drop,
                    "description": "Drop an object in your current location",
                },
                "go": {
                    "function": cls._instance.do_go,
                    "description": "Head in a direction e.g. go north (you can also use n, e, s, w))",
                },
                "build": {"function": cls._instance.do_build, "description": ""},
                "help": {
                    "function": cls._instance.do_help,
                    "description": "Get game instructions",
                },
                "inventory": {
                    "function": cls._instance.do_inventory,
                    "description": "List the objects you are carrying",
                },
                "xox": {
                    "function": cls._instance.do_shutdown,
                    # Keep this one hidden - it shuts down the game server and AI broker!
                    "description": "",
                },
            }

            # Build the commands description field from directions, synonyms and command functions
            cls._instance.commands_description = (
                "Valid directions: " + ", ".join(cls._instance.directions) + ".\n"
            )
            cls._instance.commands_description += "Synonyms: "
            for key, value in cls._instance.synonyms.items():
                cls._instance.commands_description += f"{key} = {value}, "
            cls._instance.commands_description = cls._instance.commands_description[:-2]
            cls._instance.commands_description += ".\nValid commands: "
            for command, data in cls._instance.command_functions.items():
                # Only add commands with descriptions
                if data.get("description"):
                    cls._instance.commands_description += (
                        f"{command} = {data['description']}; "
                    )
            cls._instance.commands_description = cls._instance.commands_description[:-2]

        return cls._instance

    # All these 'do_' functions are for processing commands from the player.
    # They all take the player object and the rest of the response as arguments,
    # Even if they're not needed. This is to keep the command processing simple.

    def do_go(self, player, rest_of_response):
        return self.move_player(player, rest_of_response, "")

    def do_look(self, player, rest_of_response):
        # Not used for now, next line is to avoid warnings
        rest_of_response

        message = f"You look again at the {str(player.get_current_room()).lower()}: {self.world.get_room_description(player.get_current_room())}"
        # Add buildable directions if player is a builder
        if player.role == "builder":
            message += "\n" + self.world.get_room_exits(player.get_current_room())
        return message

    def do_help(self, player, rest_of_response):
        # Not used, next line is to avoid warnings
        player, rest_of_response
        return f"Available commands:\n{self.get_commands_description()}"

    def do_say(self, player, rest_of_response, shout=False):
        verb = "shouts" if shout else "says"
        logger.info(f"User {player.player_name} {verb}: {rest_of_response}")
        if self.get_player_count() == 1:
            player_response = "You are the only player in the game currently!"
        else:
            told_count = self.tell_others(
                player.sid, f'{player.player_name} says, "{rest_of_response}"', shout
            )
            if not told_count:
                player_response = "There is no one else here to hear you!"
            else:
                player_response = f"You {verb[:-1]}, '{rest_of_response}'."
        return player_response

    def do_shout(self, player, rest_of_response):
        # Shout is the same as say but to everyone
        self.do_say(player, rest_of_response, shout=True)

    def do_wait(self, player, rest_of_response):
        # Not used, next line is to avoid warnings
        player, rest_of_response
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
            return self.move_player(player, "jump", other_player_location)
        else:
            return f"Sorry, '{other_player_name}' is not a valid player name."

    def do_shutdown(self, player, rest_of_response):
        message = f"{player.player_name} has shut down the server."
        if rest_of_response:
            message = message[:-1] + ", saying '{rest_of_response}'."
        logger.info(message)
        self.tell_everyone(message)
        # TODO: web client should do something when the back end is down, can we terminate the client too?
        # TODO: make this restart not die?
        self.sio.emit("shutdown", message)
        eventlet.sleep(1)
        sys.exit(1)

    def do_quit(self, player, rest_of_response):
        self.remove_player(player.sid, "You have left the game.")

    def do_build(self, player, rest_of_response):
        # Create a new room

        # First parse the response to get the direction, room name and description. handle the player
        # Using quotes in order to have room names and descriptions with spaces in

        # First take the direction which is one word and must be one of the directions

        direction = rest_of_response.split()[0]

        # Check direction is valid and not taken
        if direction not in self.directions:
            return f"Sorry, '{direction}' is not a valid direction."
        if direction in self.world.rooms[player.get_current_room()]["exits"]:
            return f"Sorry, there is already a room to the {direction}."

        # Remove the direction from the response
        rest_of_response = " ".join(rest_of_response.split()[1:])

        # Check if the room name is in quotes
        if rest_of_response.startswith("'") or rest_of_response.startswith('"'):
            # Find the end of the quoted string
            quote_char = rest_of_response[0]
            end_quote_index = rest_of_response.find(quote_char, 1)
            if end_quote_index == -1:
                return "Sorry, invalid input. Room name is not properly quoted."
            # Extract the room name from the quoted string
            room_name = rest_of_response[1:end_quote_index]
            # Remove the room name and any extra spaces from the response
            rest_of_response = rest_of_response[end_quote_index + 1 :].strip()
        else:
            # Room name is a single word
            room_name = rest_of_response.split()[0]
            # Remove the room name from the response
            rest_of_response = " ".join(rest_of_response.split()[1:])

        # Check the room name is valid
        if room_name == "":
            return "Sorry, invalid input. Room name is empty."
        # Check room name is not a reserved word
        if room_name in self.synonyms or room_name in self.command_functions:
            return f"Sorry, '{room_name}' is a reserved word."

        # Now take the room description, which must be in quotes
        if not rest_of_response.startswith("'") and not rest_of_response.startswith(
            '"'
        ):
            return "Sorry, invalid input. Room description must be in quotes."
        quote_char = rest_of_response[0]
        end_quote_index = rest_of_response.find(quote_char, 1)
        if end_quote_index == -1:
            return "Sorry, invalid input. Room description is not properly quoted."
        room_description = rest_of_response[1:end_quote_index]

        error_message = self.world.add_room(
            player.get_current_room(),
            direction,
            room_name,
            room_description,
            player.player_name,
        )
        # If there was an error, return it
        if error_message:
            return error_message

        # Otherwise, tell other players about the new room
        self.tell_others(
            player.sid,
            f"{player.player_name} has built to the {direction} and made a new location, {room_name}.",
            shout=True,
        )
        return f"You build {direction} and make a new location, {room_name}: {room_description}"

    # Get / pick up an object
    def do_get(self, player, rest_of_response):
        # First check in case they wrote 'pick up'. If so, remove the 'up'.
        if rest_of_response.startswith("up "):
            rest_of_response = rest_of_response[3:]
        # TODO: If in future pick is a verb e.g. pick a lock, select,
        #      we will need to pass the original verb into the functions

        # Get object name by calling a function to parse the response
        object_name = self.get_object_name_from_response(rest_of_response)

        # Check the object name is valid
        if object_name == "":
            return "Sorry, invalid input. Object name is empty."

        # Check if the object is in the room
        object = self.world.search_object(object_name, player.get_current_room())
        if object:
            # Setting player will remove the object from the room
            result = object.set_player(player)
            if not result:
                return f"You pick up {object.get_name(article='the')}."
            return result
        else:
            return f"Sorry, there is no '{object_name}' here."

    def do_inventory(self, player, rest_of_response):
        # Not used, next line is to avoid warnings
        rest_of_response
        return player.get_inventory_description()

    def do_drop(self, player, rest_of_response):
        # Get object name by calling a function to parse the response
        object_name = self.get_object_name_from_response(rest_of_response)

        # Check the object name is valid
        if object_name == "":
            return "Sorry, invalid input. Object name is empty."

        # Check if the object is in the player's inventory
        if player.drop_object(object_name):
            return f"You drop {object_name}."
        return f"Sorry, you are not carrying '{object_name}'."

    # End of 'do_' functions

    # Getters

    # Parse object name from the response after the initial verb that triggered the function
    def get_object_name_from_response(self, rest_of_response):
        # Check if the object name is in quotes
        if rest_of_response.startswith("'") or rest_of_response.startswith('"'):
            # Find the end of the quoted string
            quote_char = rest_of_response[0]
            end_quote_index = rest_of_response.find(quote_char, 1)
            if end_quote_index == -1:
                return "Sorry, invalid input. Object name is not properly quoted."
            # Extract the object name from the quoted string
            object_name = rest_of_response[1:end_quote_index]
        else:
            # Object name is a single word
            object_name = rest_of_response.split()[0]
        return object_name

    # Get a description of the commands available
    def get_commands_description(self):
        return self.commands_description

    # Get a description of the players in the game
    def get_players_text(self):
        others_count = self.get_player_count() - 1
        if others_count == 0:
            return "You are the first player to join the game.\n"
        elif others_count == 1:
            return f"You are the second player in the game.\n"
        else:
            return f"There are {others_count} other players in the game.\n"

    # Get location of player given a name
    def get_player_location_by_name(self, sid, player_name):
        for other_player in self.get_other_players(sid):
            if str(other_player.player_name).lower() == str(player_name).lower():
                return other_player.get_current_room()
        return None

    # Get number of players in the game
    def get_player_count(self):
        return len(self.players)

    # Check if a player name is unique
    def player_name_is_unique(self, player_name):
        for player_sid, player in self.players.items():
            if str(player.player_name).lower() == str(player_name).lower():
                return False
        return True

    # End of getters

    # Setters etc

    # Process player setup request from client
    def process_player_setup(self, sid, character):
        # Be defensive as this is coming from either UI or AI broker
        if "name" not in character:
            logger.error("FATAL ERROR: Player name not specified")
            exit()

        # Strip out any whitespace (defensive in case of client bug)
        player_name = character["name"].strip().title()

        # Check uniqueness here, other checks are done in the player class
        if not self.player_name_is_unique(player_name):
            # Issue with player name setting
            return "game_update", "Sorry, that name is already taken."

        # Set starting room
        starting_room = self.world.get_starting_room()

        # Create the player
        try:
            player = Player(
                self, sid, player_name, character.get("role"), starting_room
            )
        except ValueError as e:
            # Issue with player creation
            return str(e)

        # Register this player with the game server
        self.register_player(sid, player, player_name, starting_room)

        # Tell this player about the game
        instructions = (
            f"Welcome to the game, {player_name}. "
            + self.get_players_text()
            + "Please input one of these commands:\n"
            + self.get_commands_description()
        )
        for line in instructions.split("\n"):
            if line:
                self.tell_player(sid, line, type="instructions")

        # Tell this player where they are
        self.tell_player(sid, "\nThe game begins...\n")
        self.tell_player(sid, self.world.get_room_description(starting_room))

        # Tell other players about this new player
        self.tell_others(
            sid,
            f"{player_name} has joined the game, starting in the {starting_room}; there are now {self.get_player_count()} players.",
            shout=True,
        )
        self.emit_game_data_update()

        # Spawn the world-wide metadata loop when the first player is created
        # This is to minimise resource usage when no one is playing.
        self.activate_background_loop()

    # Process player input
    def process_player_input(self, player, player_input):
        player.update_last_action_time()
        player_response = ""
        if player_input:
            words = str(player_input).split()
            command = words[0].lower()
            # get the rest of the response apart from the first word
            rest_of_response = " ".join(words[1:])
            # strip out quotes from the outside of the response only
            if rest_of_response.startswith('"') and rest_of_response.endswith('"'):
                rest_of_response = rest_of_response[1:-1]
            # Do the same for single quotes
            elif rest_of_response.startswith("'") and rest_of_response.endswith("'"):
                rest_of_response = rest_of_response[1:-1]

            command = self.synonyms.get(command, command)
            logger.info(f"Command: {command}")

            # Call the function associated with a command
            if command in self.command_functions:
                player_response = self.command_functions[command]["function"](
                    player, rest_of_response
                )
            # Move the player if the command is a direction
            elif command in self.directions:
                player_response = self.move_player(player, command, rest_of_response)
            else:
                # Invalid command
                player_response = (
                    "Sorry, that is not a recognised command. Available commands:\n"
                    + self.get_commands_description()
                )
        else:
            # Empty command
            player_response = "Sorry, you need to enter a command."
        logger.info(f"Player response: {player_response}")
        return player_response

    # Handle a player's move
    def move_player(self, player, direction, next_room=None):
        # Set new room
        previous_room = player.get_current_room()
        if direction == "jump":
            # If next room specified, player has 'jumped'!
            departure_message_to_other_players = (
                f"{player.player_name} has disappeared in a puff of smoke!"
            )
            arrival_message_to_other_players = (
                f"{player.player_name} has materialised as if by magic!"
            )
        elif direction in self.world.rooms[player.get_current_room()]["exits"]:
            next_room = self.world.rooms[player.get_current_room()]["exits"][direction]

            departure_message_to_other_players = f"{player.player_name} leaves, heading {direction} to the {str(next_room).lower()}."
            arrival_message_to_other_players = (
                f"{player.player_name} arrives from the {previous_room.lower()}."
            )
        else:
            # Valid direction but no exit
            return "Sorry, you can't go that way." + self.world.get_room_exits(
                player.get_current_room()
            )

        # Check for other players you are leaving
        for other_player in self.get_other_players(player.sid):
            if other_player.get_current_room() == player.get_current_room():
                self.tell_player(
                    other_player.sid,
                    departure_message_to_other_players,
                )

        if direction == "jump":
            action = "jump"
        else:
            action = f"head {direction}"

        # Build message. only describe room if it is new to this player.
        message = f"You {action} to the {next_room.lower()}"
        if next_room in player.seen_rooms:
            message += f". {self.world.get_room_description(next_room, brief=True)}"
        else:
            message += f": {self.world.get_room_description(next_room)}"

        # Check for other players you are arriving
        for other_player in self.get_other_players(player.sid):
            if other_player.get_current_room() == next_room:
                message += f" {other_player.player_name} is here."
                self.tell_player(
                    other_player.sid,
                    arrival_message_to_other_players,
                )
        # Set new room
        player.move_to_room(next_room)
        # Emit update to player
        self.emit_player_room_update(player.sid, next_room)

        return message

    def register_player(self, sid, game, player_name, current_room):
        self.players[sid] = game
        # Keep a log of all player names including those who have left
        # This is so that when a player disconnects (e.g. closes their browser) after 'quitting' we can
        # understand that, and it will allow them to rejoin with the same name later
        self.player_sid_to_name_map[sid] = player_name
        self.emit_player_room_update(sid, current_room)
        return game

    # Emit a message about a room to a specific player
    def emit_player_room_update(self, sid, room):
        # Tell the player about the room including the image name
        self.sio.emit(
            "room_update",
            {
                "image": self.world.rooms[room]["image"],
                "title": room,
                "description": self.world.rooms[room]["description"],
            },
            sid,
        )

    # Emit a message to all players
    def tell_everyone(self, message):
        if message.strip():
            self.sio.emit("game_update", message)

    # Emit a message to all players except the one specified
    def tell_others(self, sid, message, shout=False):
        told_count = 0
        if message.strip():
            for other_game_sid, other_game in self.players.items():
                # Only tell another player if they are in the same room
                if sid != other_game_sid and (
                    shout
                    or other_game.get_current_room()
                    == self.players[sid].get_current_room()
                ):
                    self.sio.emit("game_update", message, other_game_sid)
                    told_count += 1
        return told_count

    # Emit a message to a specific player
    def tell_player(self, sid, message, type="game_update"):
        if message.strip():
            self.sio.emit(type, message, sid)

    # Get other players
    def get_other_players(self, sid):
        other_players = []
        for other_game_sid, other_game in self.players.items():
            if sid != other_game_sid:
                other_players.append(other_game)
        return other_players

    # Emit game data update to all players
    def emit_game_data_update(self):
        if self.get_player_count() > 0:
            game_data = {"player_count": self.get_player_count()}
            self.sio.emit(
                "game_data_update",
                game_data,
            )

    # Check each player to see if they have been inactive for too long
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

    # Remove a player from the game
    def remove_player(self, sid, reason):
        if sid in self.players:
            player = self.players[sid]
            self.tell_player(
                player.sid,
                reason,
            )
            message = f"{player.player_name} has left the game; there are now {self.get_player_count()-1} players."
            logger.info(message)
            self.tell_others(
                sid,
                message,
                shout=True,
            )
            self.emit_game_data_update()
            self.sio.emit("logout", None, sid)
            # Check again (race condition)
            if sid in self.players:
                del self.players[sid]
            # If there are no players left, stop the background loop
            if self.get_player_count() == 0:
                self.deactivate_background_loop()
        else:
            logger.info(
                f"Player with SID {sid} ({self.player_sid_to_name_map.get(sid,'name unknown')}) has already been removed, they probably quit before."
            )

    # Spawn the world-wide metadata loop when the first player is created
    def activate_background_loop(self):
        if not self.background_loop_active:
            logger.info("Activating background loop.")
            self.background_loop_active == True
            eventlet.spawn(self.game_background_loop)

    # Cause the game background loop to exit
    def deactivate_background_loop(self):
        logger.info("Deactivating background loop.")
        self.background_loop_active == False

    # This loop runs in the background to do things like broadcast player count
    # It only runs when there are players in the game
    def game_background_loop(self):
        while self.background_loop_active:
            # Time out players who do nothing for too long.
            self.check_players_activity()

            # For now, the only thing happening is broadcast of player count
            # So that AI players can pause when there are no human players, saving money
            self.emit_game_data_update()

            eventlet.sleep(60)
