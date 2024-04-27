from logger import setup_logger, exit

# Set up logger first
logger = setup_logger()

from typing import Dict, Callable, Tuple, Optional, Union
from player import Player
from world import World
from aimanager import AIManager
from gamemanager import GameManager


class PlayerInputProcessor:

    def __init__(self, game_manager: GameManager):
        self.game_manager = game_manager
        self.setup_commands()

    def setup_commands(self) -> None:

        self.directions = ["north", "east", "south", "west"]

        self.synonyms: Dict[str, str] = {
            "n": "north",
            "e": "east",
            "s": "south",
            "w": "west",
            "pick": "get",
            "take": "get",
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
            "press": "push",
            "kill": "attack",
            "hit": "attack",
        }

        self.command_functions: Dict[str, Dict[str, Callable]] = {
            # TODO #66 Limit certain actions to players with the right permissions rather than just hiding from help
            "look": {
                "function": self.game_manager.do_look,
                "description": "Get a description of your current location",
            },
            "say": {
                "function": self.game_manager.do_say,
                "description": "Say something to all other players in your *current* location, e.g. say which way shall we go?",
            },
            "shout": {
                "function": self.game_manager.do_shout,
                "description": "Shout something to everyone in the game, e.g. shout Where is everyone?",
            },
            "greet": {
                "function": self.game_manager.do_greet,
                "description": "Say hi to someone, e.g. 'greet Ben' is the same as 'say Hi Ben'. Hint: you can also just write 'hi Ben'!",
            },
            "wait": {
                "function": self.game_manager.do_wait,
                "description": "Do nothing for now",
            },
            "jump": {
                "function": self.game_manager.do_jump,
                "description": "Jump to location of another player named in rest_of_response",
            },
            "attack": {
                "function": self.game_manager.do_attack,
                "description": "",  # Not supported
            },
            "quit": {
                "function": self.game_manager.do_quit,
                "description": "",  # Don't encourage the AI to quit! TODO: make this only appear in the help to human players
            },
            "get": {
                "function": self.game_manager.do_get,
                "description": "Pick up an item in your current location",
            },
            "drop": {
                "function": self.game_manager.do_drop,
                "description": "Drop an item in your current location",
            },
            "go": {
                "function": self.game_manager.do_go,
                "description": "Head in a direction e.g. go north (you can also use n, e, s, w))",
            },
            "build": {
                "function": self.game_manager.do_build,
                "description": "Build a new location. Specify the direction, name and description using single quotes "
                + "e.g: build west 'Secluded Clearing' 'A small, but beautiful clearing in the middle of a forest.'.'",
            },
            "buy": {
                "function": self.game_manager.do_buy,
                "description": "Buy an item from an entity (e.g. a Merchant) in your current location.",
            },
            "sell": {
                "function": self.game_manager.do_sell,
                "description": "Sell an item to an entity (e.g. a Merchant) in your current location.",
            },
            "trade": {
                "function": self.game_manager.do_trade,
                "description": "Enter into trading negotiations with a Merchant in your current location.",
            },
            "push": {
                "function": self.game_manager.do_push,
                "description": "Push something in your possession, a button for example...",
            },
            "inventory": {
                "function": self.game_manager.do_inventory,
                "description": "List the items you are carrying",
            },
            "xox": {
                "function": self.game_manager.do_shutdown,
                # Keep this one hidden - it shuts down the game server and AI broker!
                "description": "",
            },
            # Help is special, as it doesn't need a function to be defined in the game manager, it can be handled here
            "help": {
                "function": self.get_help_text,
                "description": "Get game instructions",
            },
        }

        # Build the commands description field from directions, synonyms and command functions
        self.commands_description: str = "Valid directions: " + ", ".join(
            self.directions
        )
        self.commands_description += ".\nValid commands: "
        for command, data in self.command_functions.items():
            # Only add commands with descriptions
            if data.get("description"):
                self.commands_description += f"{command} = {data['description']}; "
        self.commands_description = self.commands_description[:-2]
        self.commands_description += ". Recognised synonyms: "
        for key, value in self.synonyms.items():
            # Only show synonyms to commands that have a description
            if value in self.command_functions and self.command_functions[value].get(
                "description"
            ):
                self.commands_description += f"{key} = {value}, "
        self.commands_description = self.commands_description[:-2]

    def get_help_text(
        self, player: Optional[Player] = None, rest_of_response: Optional[str] = None
    ) -> str:
        return (
            self.game_manager.world.get_objective()
            + " "
            + self.game_manager.get_players_text()
            + f"\nAvailable commands:\n{self.get_commands_description()}"
        )

    # Get a description of the commands available
    def get_commands_description(self) -> str:
        return self.commands_description

    # Strip outer quotes from a string
    def strip_outer_quotes(self, some_text: str) -> None:
        if (
            some_text.startswith('"')
            and some_text.endswith('"')
            or some_text.startswith("'")
            and some_text.endswith("'")
        ):
            some_text = some_text[1:-1]
        return some_text

    # Resolve the room name from the rest of the response
    def resolve_room_name(self, rest_of_response: str) -> Tuple[str, str, str]:
        if rest_of_response.startswith("'") or rest_of_response.startswith('"'):
            # Find the end of the quoted string
            quote_char: str = rest_of_response[0]
            end_quote_index: int = rest_of_response.find(quote_char, 1)
            if end_quote_index == -1:
                return "", "", "Invalid input: room name is not properly quoted."
            # Extract the room name from the quoted string
            room_name: str = rest_of_response[1:end_quote_index]
            # Remove the room name and any extra spaces from the response
            rest_of_response = rest_of_response[end_quote_index + 1 :].strip()
        else:
            # Room name is a single word
            room_name: str = rest_of_response.split()[0]
            # Remove the room name from the response
            rest_of_response = " ".join(rest_of_response.split()[1:])

        # Check the room name is valid
        if room_name == "":
            return "", "", "Invalid input: room name is empty."
        # Check room name is not a reserved word
        if (
            room_name.lower() in self.synonyms
            or room_name.lower() in self.command_functions
        ):
            return "", "", f"'{room_name}' is a reserved word."
        logger.info(
            f"Resolved room name {room_name}, rest of response <{rest_of_response}>"
        )
        return room_name.capitalize(), rest_of_response, ""

    # Parse player input
    def parse_player_input(self, player_input: str) -> Tuple[str, str]:
        player_input = player_input.strip(".")
        # Special handling of leading apostrophe (means say):
        if player_input.startswith("'"):
            player_input = player_input.strip("'")
            player_input = "say " + player_input
        # Separate first word (command) from rest
        words = str(player_input).split()
        verb = words[0].lower()
        rest = " ".join(words[1:])
        # strip out quotes from the outside of the response only
        rest = self.strip_outer_quotes(rest)
        return verb, rest

    # Translate player input and try to process it again
    def translate_and_process(self, player: Player, player_input: str) -> Optional[str]:
        # Try to translate the user input into a valid command using AI :-)
        self.tell_player(player, "I'm trying to guess what you meant by that...")
        prompt: str = (
            "Help me to translate my user's input into a valid adventure game command.\n"
            + self.get_commands_description()
            + "\nRespond with only a valid command, nothing else.\n"
            + player.get_input_history(
                10, "Some history of what the user has seen for context:"
            )
            + f"Their latest input to translate: {player_input}"
        )
        ai_translation: Optional[str] = self.ai_manager.submit_request(prompt)
        logger.info("AI translation: %s", ai_translation)
        if ai_translation:
            # Try to process the AI translation as a command, but only try this once
            self.tell_player(
                player,
                f"I think you meant '{ai_translation}', and will proceed accordingly. ",
            )
            return self.process_player_input(player, ai_translation, translated=True)
        return None

    def check_direction(self, direction: str, player: Player) -> str:
        if direction not in self.directions:
            return f"'{direction}' is not a valid direction."

    # Process player input. Returns a function pointer, a tuple of arguments, and an error message if any.
    def process_player_input(
        self, player: Player, player_input: str, translated: bool = False
    ) -> Optional[
        Tuple[
            Callable, Union[Tuple[Player, str], Tuple[Player, str, str], Optional[str]]
        ]
    ]:
        player.update_last_action_time()
        if not player_input:
            # Empty command
            return "You need to enter a command."

        player.add_input_history(f"You: {player_input}")

        # get the rest of the response apart from the first word
        command: str
        rest_of_response: str
        command, rest_of_response = self.parse_player_input(player_input)

        # Check for synonyms
        command = self.synonyms.get(command, command)
        logger.info(f"Command: {command}")

        # Resolve the function associated with a command, and its parameters.
        if command in self.command_functions:
            # Special handling for build command: validate the room name and pass it as an extra parameter
            if command == "build":

                # First parse the response to get the direction, room name and description. handle the player
                # Using quotes in order to have room names and descriptions with spaces in

                # First take the direction which is one word and must be one of the directions
                direction: str = rest_of_response.split()[0]

                # Check direction is valid and not taken
                outcome: str = self.check_direction(direction, player)
                if outcome:
                    return outcome

                # Remove the direction from the response
                rest_of_response: str = " ".join(rest_of_response.split()[1:])
                if not rest_of_response:
                    # User did not specify name of room to build
                    return "Please specify room name in quotes and a description."

                # Check if the room name is in quotes
                room_name: str
                room_description: str
                error: str
                room_name, room_description, error = self.resolve_room_name(
                    rest_of_response
                )
                if error:
                    return None, None, error
                # Check room description is in quotes if given
                if room_description:
                    if not room_description.startswith(
                        "'"
                    ) and not room_description.startswith('"'):
                        return (
                            None,
                            None,
                            "Invalid input: room description must be in quotes.",
                        )
                    else:
                        # Quoted room description given by user
                        quote_char: str = room_description[0]
                        end_quote_index: int = room_description.find(quote_char, 1)
                        if end_quote_index == -1:
                            return (
                                None,
                                None,
                                "Invalid input: room description is not properly quoted.",
                            )
                        room_description = self.strip_outer_quotes(room_description)
                return (
                    self.command_functions[command]["function"],
                    (player, direction, room_name, room_description),
                    None,
                )
            # Normal command
            return (
                self.command_functions[command]["function"],
                (
                    player,
                    rest_of_response,
                ),
                None,
            )
        # Different return if the command is a direction
        elif command in self.directions:
            return (
                self.game_manager.move_entity,
                (player, command, rest_of_response),
                None,
            )
        else:
            # If the command is not recognised, try to translate it using AI (unless this is already a translation)
            if not translated:
                return self.translate_and_process(player, player_input)
            # Invalid command
            return (
                None,
                None,
                (
                    "That is not a recognised command. Available commands:\n"
                    + self.get_commands_description()
                ),
            )
