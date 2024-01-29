from logger import setup_logger

# Set up logger
logger = setup_logger()


# Cheeky little debug function
import traceback


def dbg(thing=None):
    # print stack trace
    traceback.print_stack()
    print(f"DEBUG: <{str(thing)}>")


import eventlet
import time
import sys
from player import Player
from world import World
import aimanager


class GameManager:
    _instance = None

    def __new__(cls, sio, mode=None):
        if cls._instance is None:
            cls._instance = super(GameManager, cls).__new__(cls)

            # Static variables
            cls._instance.max_inactive_time = 300  # 5 minutes
            cls._instance.background_loop_active = False

            # Set up game state
            cls._instance.sio = sio
            cls._instance.players = {}
            cls._instance.player_sid_to_name_map = {}
            cls._instance.world = World(mode)

            # TODO: resolve this from the rooms document
            cls._instance.synonyms = {
                "n": "north",
                "e": "east",
                "s": "south",
                "w": "west",
                # "exit": "quit", #AI tries exit to leave a room :-(
                "pick": "get",
                "head": "go",
                "walk": "go",
                "run": "go",
                "enter": "go",
                "hi": "greet",
                "talk": "say",
                "inv": "inventory",
                "haggle": "trade",
                "purchase": "buy",
                "examine": "look",
                "inspect": "look",
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
                "greet": {
                    "function": cls._instance.do_greet,
                    "description": "Say hi to someone, e.g. 'greet Ben' is the same as 'say Hi Ben'. Hint: you can also just write 'hi Ben'!",
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
                "go": {
                    "function": cls._instance.do_go,
                    "description": "Head in a direction e.g. go north (you can also use n, e, s, w))",
                },
                "build": {
                    "function": cls._instance.do_build,
                    "description": "Build a new location. Specify the direction, name and description using single quotes "
                    + "e.g: build west 'Secluded Clearing' 'A small, but beautiful clearing in the middle of a forest.'.'",
                },
                "buy": {
                    "function": cls._instance.do_buy,
                    "description": "Buy an object from a character (e.g. a Merchant) in your current location.",
                },
                "sell": {
                    "function": cls._instance.do_sell,
                    "description": "Sell an object to a character (e.g. a Merchant) in your current location.",
                },
                "trade": {
                    "function": cls._instance.do_trade,
                    "description": "Enter into trading negotiations with a Merchant in your current location.",
                },
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
        # Strip off at and the
        if rest_of_response and rest_of_response[0:3] == "at ":
            rest_of_response = rest_of_response[3:]
            if rest_of_response[0:4] == "the ":
                rest_of_response = rest_of_response[4:]
            if rest_of_response == "":
                return "Look at what?"
        if rest_of_response:
            # Find what they are looking at
            object_name = self.get_object_name_from_response(rest_of_response)
            # Check if the object is in the room
            object = self.world.search_object(object_name, player.get_current_room())
            if not object:
                # Try to find the object in the player's inventory
                for inv_object in player.get_inventory():
                    if object_name.lower() in inv_object.get_name().lower():
                        object = inv_object
                        break
                # Try to find the object in the possession of a merchant
                if not object:
                    for merchant in self.get_merchants(player.get_current_room()):
                        for merchant_object in merchant.get_inventory():
                            if (
                                object_name.lower()
                                in merchant_object.get_name().lower()
                            ):
                                object = merchant_object
                                break
            if object:
                return f"You look at {object.get_name(article='the')}: {object.get_description()}"
            # Check if they named a character
            character = self.is_character(object_name)
            if character:
                return character.get_description()
            return f"Sorry, there is no '{object_name}' here."
        else:
            # Looking at the room
            message = (
                f"You look again at the "
                + str(player.get_current_room()).lower()
                + ": "
                + self.world.get_room_description(
                    player.get_current_room(), brief=False, role=player.get_role()
                )
            )
            # Add buildable directions if player is a builder
            if player.role == "builder":
                message += "\n" + self.world.get_room_exits(player.get_current_room())
            return message

    def do_help(self, player=None, rest_of_response=None):
        # Not used, next line is to avoid warnings
        player, rest_of_response
        return (
            self.world.get_objective()
            + self.get_players_text()
            + f"\nAvailable commands:\n{self.get_commands_description()}"
        )

    def do_say(self, player, rest_of_response, shout=False):
        verb = "shouts" if shout else "says"
        # Remove 'to' and player name
        if rest_of_response.startswith("to "):
            # Split rest of response into player name and message
            other_player_name, rest_of_response = rest_of_response[3:].split(" ", 1)
            if self.is_existing_player_name(other_player_name):
                if rest_of_response == "":
                    return f"Say what to {other_player_name}?"
                else:
                    return "You can't currently speak to just one person in the room. To converse, just use 'say' followed by what you want to say, everyone in the room will hear you."
            else:
                return f"{other_player_name} is not in the game!"

        logger.info(f"User {player.name} {verb}: {rest_of_response}")
        if self.get_player_count() == 1:
            player_response = "You are the only player in the game currently!"
        else:
            told_count = self.tell_others(
                player.sid, f'{player.name} says, "{rest_of_response}"', shout
            )
            if not told_count:
                player_response = "There is no one else here to hear you!"
            else:
                player_response = f"You {verb[:-1]}, '{rest_of_response}'."
        return player_response

    def do_shout(self, player, rest_of_response):
        # Shout is the same as say but to everyone
        self.do_say(player, rest_of_response, shout=True)

    def do_greet(self, player, rest_of_response):
        # Like say hi!
        self.do_say(player, "Hi " + rest_of_response)

    def do_wait(self, player, rest_of_response):
        # Not used, next line is to avoid warnings
        player, rest_of_response
        return "You decide to just wait a while."

    def do_jump(self, player, rest_of_response):
        # Jump to location of another player named in rest_of_response
        other_character_name = rest_of_response
        # find location of other player
        other_character_location = self.get_player_location_by_name(
            player.sid, other_character_name
        )
        # if found, move player there
        if other_character_location:
            return self.move_player(player, "jump", other_character_location)
        else:
            return f"Sorry, '{other_character_name}' is not a valid player name."

    def do_shutdown(self, player, rest_of_response):
        message = f"{player.name} has shut down the server."
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
            player.name,
        )
        # If there was an error, return it
        if error_message:
            return error_message

        # Otherwise, tell other players about the new room
        self.tell_others(
            player.sid,
            f"{player.name} has built to the {direction} and made a new location, {room_name}.",
            shout=True,
        )
        return f"You build {direction} and make a new location, {room_name}: {room_description}"

    def is_character(self, object_name):
        for other_character in self.get_other_characters():
            if (
                str(other_character.name).lower() == str(object_name).lower()
                or other_character.get_role() == object_name.lower()
            ):
                return other_character
        return False

    def get_merchants(self, room=None):
        # Merchants are characters of a certain type.
        # If a room is specified, only return merchants in that room
        merchants = []
        for npc in self.world.npcs:
            if npc.get_role() == "merchant":
                if room is None or npc.get_current_room() == room:
                    merchants.append(npc)
        return merchants

    # Check if an object is in a merchant's possession
    def transact_object(self, object_name, player, action="get"):
        for merchant in self.get_merchants(player.get_current_room()):
            if action == "sell":
                for object in player.get_inventory():
                    if object.get_name().lower() == object_name.lower():
                        # Add the money to the player's inventory
                        player.add_money(object.get_price())
                        # NOTE: Merchant has unlimited money for now at least
                        # Change object ownership
                        object.transfer(player, merchant)
                        return f"You sell {object.get_name(article='the')} to {merchant.get_name()} for {self.world.get_currency(object.get_price())}."
                return "That object is not in your inventory."
            else:
                # Don't go any further if pockets are full!
                if not player.can_add_object():
                    return f"Sorry, you can't carry any more."
                for object in merchant.get_inventory():
                    if object.get_name().lower() == object_name.lower():
                        if action == "get":
                            # Simply return True if the object is in the merchant's possession and the player said to get not buy
                            # As we can't assume they were willing to buy it
                            return f"The object '{object.get_name()}' is in the possession of a merchant. Perhaps you can purchase it?"
                        elif action == "buy":
                            # Simply return True if the object is in the merchant's possession and the player said to buy
                            if player.deduct_money(object.get_price()):
                                issue = object.transfer(merchant, player)
                                if not issue:
                                    # Tell the others about the transaction
                                    self.tell_others(
                                        player.sid,
                                        f"{player.name} has bought {object.get_name(article='the')} from {merchant.get_name()}.",
                                    )
                                    return f"Congratulations, you successfully purchased {object.get_name(article='the')} for {self.world.get_currency(object.get_price())}."

                                return issue

                            else:
                                return f"Sorry, you do not have enough money to buy {object.get_name(article='the')}."
        # If we get here, the object is not in any merchant's possession
        return ""

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
        # Check if they named a character
        elif self.is_character(object_name):
            return f"I would advise against picking up {object_name}, they will not react well!"
        # Check if the object is in the possession of a merchant
        else:
            outcome = self.transact_object(object_name, player, "get")
            if outcome:
                return outcome
            return f"Sorry, there is no '{object_name}' here."

    def do_inventory(self, player, rest_of_response):
        # Not used, next line is to avoid warnings
        rest_of_response
        return player.get_inventory_description()

    def get_object_list_text(self, objects):
        drop_list_text = ""
        drop_count = 0
        for object in objects:
            drop_count += 1
            if drop_count > 1:
                if drop_count == len(objects):
                    drop_list_text += " and "
                else:
                    drop_list_text += ", "
            drop_list_text += f"{object.get_name(article='the')}"
        drop_list_text += "."
        return drop_list_text

    def do_drop(self, player, rest_of_response):
        # Get object name by calling a function to parse the response
        object_name = self.get_object_name_from_response(rest_of_response)

        # Check the object name is valid
        if object_name == "":
            return "Sorry, invalid input. Object name is empty."

        # Check if the object is in the player's inventory, if so, drop it
        # "all" is a special case to drop everything
        objects = player.drop_object(object_name)
        if objects:
            drop_list_text = self.get_object_list_text(objects)
            # Tell the others about the drop
            self.tell_others(
                player.sid,
                f"{player.name} has dropped {drop_list_text}",
            )
            return "You drop " + drop_list_text
        else:
            if object_name == "all":
                return f"You are not carrying anything."
            else:
                return f"Sorry, you are not carrying '{object_name}'."

    def do_buy(self, player, rest_of_response):
        # Get object name by calling a function to parse the response
        object_name = self.get_object_name_from_response(rest_of_response)

        # Check the object name is valid
        if object_name == "":
            return "Sorry, invalid input. Object name is empty."

        # Check if the object is in the room
        object = self.world.search_object(object_name, player.get_current_room())
        if object:
            # Can just pick it up
            return "You don't have to buy that, you can just pick it up!"
        # Check if they named a character
        elif self.is_character(object_name):
            return f"That character is not for sale!"
        # Check if the object is in the possession of a merchant
        else:
            outcome = self.transact_object(object_name, player, "buy")
            if outcome:
                return outcome
            return f"Sorry, there is no '{object_name}' here."

    def do_sell(self, player, rest_of_response):
        # Get object name by calling a function to parse the response
        object_name = self.get_object_name_from_response(rest_of_response)
        # Check the object name is valid
        if object_name == "":
            return "Sorry, invalid input. Object name is empty."

        # Check if the object is in the player's inventory
        for object in player.get_inventory():
            if (
                object_name.lower() in object.get_name().lower()
                or object_name.lower() == "all"
            ):
                if not object.get_price():
                    return f"You can't sell {object.get_name(article='the')}."
                # Try to sell it to a merchant
                outcome = self.transact_object(object_name, player, "sell")
                if outcome:
                    return outcome
                return f"Sorry, there is no merchant here to sell {object.get_name(article='the')} to."
        return f"Sorry, you are not carrying '{object_name}'."

    def do_trade(self, player, rest_of_response):
        # TODO - support this :-)
        return "Support for this command coming soon!"

    # End of 'do_' functions

    # Getters

    # Parse object name from the response after the initial verb that triggered the function
    def get_object_name_from_response(self, rest_of_response):
        if rest_of_response == "everything" or rest_of_response == "*":
            return "all"
        # This is now simple because quotes are stripped out earlier
        return rest_of_response

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
        for other_character in self.get_other_characters(sid):
            if str(other_character.name).lower() == str(player_name).lower():
                return other_character.get_current_room()
        return None

    # Get number of players in the game
    def get_player_count(self):
        return len(self.players)

    # Check if a player name is unique
    def is_existing_player_name(self, player_name):
        for player_sid, player in self.players.items():
            if str(player.name).lower() == str(player_name).lower():
                return True
        return False

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
        if self.is_existing_player_name(player_name):
            # Issue with player name setting
            return "game_update", "Sorry, that name is already taken."
        if player_name == "system":
            # Do not let any player be called system
            return "game_update", "Sorry, that name is reserved."

        # Create the player
        try:
            player = Player(self.world, sid, player_name, character.get("role"))
        except ValueError as e:
            # Issue with player creation
            return str(e)

        # Register this player with the game server
        self.register_player(sid, player, player_name)

        # Tell other players about this new player
        self.tell_others(
            sid,
            f"{player_name} has joined the game, starting in the {player.get_current_room()}; there are now {self.get_player_count()} players.",
            shout=True,
        )

        # Tell this player about the game
        instructions = f"Welcome to the game, {player_name}. " + self.do_help()

        self.tell_player(player, instructions, type="instructions")

        self.tell_player(
            player, self.move_player(player, "join", player.get_current_room())
        )

        self.emit_game_data_update()

        # Spawn the world-wide metadata loop when the first player is created
        # This is to minimise resource usage when no one is playing.
        self.activate_background_loop()

    # Process player input
    def process_player_input(self, player, player_input, translated=False):
        player.update_last_action_time()
        player_response = ""
        if player_input:
            # Special handling of leading apostrophe (means say):
            if player_input.startswith("'"):
                player_input = player_input.strip("'")
                player_input = "say " + player_input

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
                # If the command is not recognised, try to translate it using AI (unless this is already a translation)
                if not translated:
                    # Try to translate the user input into a valid command using AI :-)
                    ai_translation = aimanager.submit_prompt(
                        "Please help me to translate my user's input into a valid adventure game command.\n"
                        + "Valid commands:"
                        + self.get_commands_description()
                        + "\nRespond with only a valid command, nothing else.\n"
                        + f"Some history of what the user has seen for context:\n{player.get_input_history(10)}\n"
                        + f"Their input: {player_input}",
                    )
                    logger.info(f"AI translation: {ai_translation}")
                    if ai_translation:
                        # Try to process the AI translation as a command, but only try this once
                        player_response = self.process_player_input(
                            player, ai_translation, translated=True
                        )
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
            departure_message = f"{player.name} has disappeared in a puff of smoke!"
            arrival_message = f"{player.name} has materialised as if by magic!"
        elif direction == "join":
            departure_message = ""
            arrival_message = ""  # Covered elsewhere
        elif direction in self.world.rooms[player.get_current_room()]["exits"]:
            next_room = self.world.rooms[player.get_current_room()]["exits"][direction]

            departure_message = f"{player.name} leaves, heading {direction} to the {str(next_room).lower()}."
            arrival_message = f"{player.name} arrives from the {previous_room.lower()}."
        elif direction in self.directions:
            # Valid direction but no exit
            return f"Sorry, you can't go {direction}." + self.world.get_room_exits(
                player.get_current_room()
            )
        else:
            # Not a valid direction

            # First check in case a room is mentioned
            # Loop through the exits to see if any of them match the room name
            for exit_dir, exit_room in self.world.rooms[player.get_current_room()][
                "exits"
            ].items():
                if exit_room.lower() in direction.lower():
                    return self.move_player(player, exit_dir)

            return f"{direction} is not a valid direction or room name."

        # Check for other players you are leaving
        for other_character in self.get_other_characters(player.sid, players_only=True):
            if other_character.get_current_room() == player.get_current_room():
                self.tell_player(
                    other_character,
                    departure_message,
                )

        if direction == "jump":
            action = "jump to"
        if direction == "join":
            action = "start in"
        else:
            action = f"head {direction} to"

        # Build message. only describe room if it is new to this player.
        message = f"You {action} the {next_room.lower()}"
        if next_room in player.seen_rooms:
            message += f". {self.world.get_room_description(next_room, brief=True, role=player.get_role())}"
        else:
            message += f": {self.world.get_room_description(next_room, role=player.get_role())}"

        # Check for other characters who are already where you are arriving.
        for other_character in self.get_other_characters(player.sid):
            if other_character.get_current_room() == next_room:
                message += f" {other_character.get_name()} is here."
                if other_character.get_role() == "merchant":
                    message += " " + other_character.get_inventory_description()
                # Only tell players not nps that you have arrived
                if other_character.get_is_player():
                    self.tell_player(
                        other_character,
                        arrival_message,
                    )
        # Set new room
        player.move_to_room(next_room)
        # Emit update to player
        self.emit_player_room_update(player, next_room)

        return message

    def register_player(self, sid, game, player_name):
        self.players[sid] = game
        # Keep a log of all player names including those who have left
        # This is so that when a player disconnects (e.g. closes their browser) after 'quitting' we can
        # understand that, and it will allow them to rejoin with the same name later
        self.player_sid_to_name_map[sid] = player_name
        # self.emit_player_room_update(sid, current_room)
        return game

    # Emit a message about a room to a specific player
    def emit_player_room_update(self, player, room):
        # Tell the player about the room including the image name
        self.sio.emit(
            "room_update",
            {
                "image": self.world.rooms[room]["image"],
                "title": room,
                "description": self.world.get_room_description(
                    room,
                    brief=False,
                    role=player.get_role(),
                    show_objects=False,
                    show_exits=False,
                ),
                "exits": self.world.get_room_exits(room),
            },
            player.sid,
        )

    # Emit a message to all players
    def tell_everyone(self, message):
        self.tell_others(None, message, shout=True)

    # Emit a message to all players except the one specified
    def tell_others(self, sid, message, shout=False):
        told_count = 0
        if message.strip():
            for other_player_sid, other_player in self.players.items():
                # Only tell another player if they are in the same room
                if sid != other_player_sid and (
                    shout
                    or other_player.get_current_room()
                    == self.players[sid].get_current_room()
                ):
                    self.tell_player(other_player, message)
                    told_count += 1
        return told_count

    # Emit a message to a specific player
    def tell_player(self, player, message, type="game_update"):
        message = message.strip()
        for line in message.split("\n"):
            if line != "":
                self.sio.emit(type, line, player.sid)
                player.add_input_history(line)

    # Get other players
    def get_other_characters(self, sid=None, players_only=False):
        other_characters = []
        for other_game_sid, other_game in self.players.items():
            if sid is None or sid != other_game_sid:
                other_characters.append(other_game)
        if not players_only:
            other_characters.extend(self.world.npcs)
        return other_characters

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
            # Make player drop all objects in their inventory
            self.tell_player(player, self.do_drop(player, "all"))
            # TODO: create coin objects corresponding to their money
            self.tell_player(
                player,
                reason,
            )
            message = f"{player.name} has left the game; there are now {self.get_player_count()-1} players."
            logger.info(message)
            self.tell_others(
                sid,
                message,
                shout=True,
            )
            self.emit_game_data_update()
            # Give player time to read the messages before logging them out
            eventlet.sleep(2)
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
