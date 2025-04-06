from utils import set_up_logger, exit

# Set up logger first
logger = set_up_logger()

from typing import Dict, Callable, Tuple, Optional, Union, List
from person import Person
from world import World
from worldmanager import WorldManager
import re


class UserInputProcessor:

    def __init__(self, world_manager: WorldManager):
        self.world_manager = world_manager
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
            # TODO #66 Limit certain actions to people with the right permissions rather than just hiding from help
            "look": {
                "function": self.world_manager.do_look,
                "description": "Get a description of your current location",
            },
            "say": {
                "function": self.world_manager.do_say,
                "description": "Say something to all other people in your *current* location, e.g. say which way shall we go?",
            },
            "shout": {
                "function": self.world_manager.do_shout,
                "description": "Shout something to everyone in the world, e.g. shout Where is everyone?",
            },
            "greet": {
                "function": self.world_manager.do_greet,
                "description": "Say hi to someone, e.g. 'greet Ben' is the same as 'say Hi Ben'. Hint: you can also just write 'hi Ben'!",
            },
            "wait": {
                "function": self.world_manager.do_wait,
                "description": "Do nothing for now",
            },
            "jump": {
                "function": self.world_manager.do_jump,
                "description": "Jump to location of another person named in rest_of_response",
            },
            "attack": {
                "function": self.world_manager.do_attack,
                "description": "",  # Not supported
            },
            "quit": {
                "function": self.world_manager.do_quit,
                "description": "",  # Don't encourage the AI to quit! TODO: make this only appear in the help to human people
            },
            "get": {
                "function": self.world_manager.do_get,
                "description": "Pick up an item in your current location",
            },
            "drop": {
                "function": self.world_manager.do_drop,
                "description": "Drop an item in your current location",
            },
            "go": {
                "function": self.world_manager.do_go,
                "description": "Head in a direction e.g. go north (you can also use n, e, s, w))",
            },
            "build": {
                "function": self.world_manager.do_build,  # Called with special inputs - see process_user_input below
                "description": "Build a new location. Specify the direction, name and description (avoid confusion by not describing specific items, those are created separately) using single quotes "
                + "e.g: build west 'Secluded Clearing' 'A small, but beautiful clearing in the middle of a forest'",
            },
            "create": {
                "function": self.world_manager.do_create,
                "description": "Create a new item. Specify the name and description using single quotes "
                + "e.g: create 'burnt sausage' 'A British pork sausage that looks cooked, at least it is burnt on the outside'",
            },
            "spawn": {
                "function": self.world_manager.do_spawn,
                "description": (
                    "Create a new animal. Specify the name, description and a list of actions the animal performs, using single quotes for each"
                    + "e.g: create 'smiling fox' "
                    + "'A plump, healthy-looking fox with a permanent cheeky smile on its face' "
                    + "'yawns, stretches, wags its tail, looks around, sniffs the air, scratches its ear'"
                ),
            },
            "summon": {
                "function": self.world_manager.do_summon,
                "description": (
                    ""  # Hidden from AI for now
                    # "Summon a new person into the world. Specify the instructions for the new person using single quotes "
                    # + "e.g: summon 'You are a brave adventurer. Your mission is to find the treasure.'"
                ),
            },
            "buy": {
                "function": self.world_manager.do_buy,
                "description": "Buy an item from an entity (e.g. a Merchant) in your current location.",
            },
            "sell": {
                "function": self.world_manager.do_sell,
                "description": "Sell an item to an entity (e.g. a Merchant) in your current location.",
            },
            "trade": {
                "function": self.world_manager.do_trade,
                "description": "Enter into trading negotiations with a Merchant in your current location.",
            },
            "inventory": {
                "function": self.world_manager.do_inventory,
                "description": "List the items you are carrying",
            },
            "xox": {
                "function": self.world_manager.do_shutdown,
                # Keep this one hidden - it shuts down the Orchestrator and AI broker!
                "description": "",
            },
            # Help is special, as it doesn't need a function to be defined in the world manager, it can be handled here
            "help": {
                "function": self.get_help_text,
                "description": "Get world instructions",
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
        self, person: Optional[Person] = None, rest_of_response: Optional[str] = None
    ) -> str:
        objective = self.world_manager.world.get_objective(person)
        return (
            objective
            + " "
            + self.world_manager.get_people_text()
            + f"\nAvailable commands:\n{self.get_commands_description()}"
        )

    # Get a description of the commands available
    def get_commands_description(self) -> str:
        return self.commands_description

    def strip_outer_quotes(self, some_text: str) -> str:
        # Regular expression to match a single set of quotes around the whole string
        pattern = r'^(["\']).*\1$'

        if re.match(pattern, some_text):
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

    # Parse person input
    def parse_user_input(self, user_input: str) -> Tuple[str, str]:
        user_input = user_input.strip(".")
        # Special handling of leading apostrophe (means say):
        if user_input.startswith("'"):
            user_input = user_input.strip("'")
            user_input = "say " + user_input
        # Separate first word (command) from rest
        words = str(user_input).split()
        verb = words[0].lower()
        rest = " ".join(words[1:])
        return verb, rest

    # Translate person input and try to process it again
    async def translate_and_process(
        self, person: Person, user_input: str
    ) -> Optional[Tuple[str, str, str]]:
        # Try to translate the user input into a valid command using AI :-)
        # If output set, it shows the user something while the AI is working.
        output: str = ""  # Was: I'm trying to guess what you meant by that...
        prompt: str = (
            "Help me to translate my person's input into either a valid command, or a custom action.\n"
            + self.get_commands_description()
            + person.get_input_history(
                10, "Some history of what the user has seen for context:"
            )
            + "\nThe person's current location description: "
            + self.world_manager.world.rooms[person.get_current_location()].description
            + "\nThe items in this location: "
            + self.world_manager.world.get_room_items_description(
                person.get_current_location()
            )
            + f"\nPerson's inventory: {person.get_inventory_description()}"
            + f"\nPerson's input: {user_input}"
            + "\nIf the person did not mean one of the above commands or the person references an item that is not listed, please respond with the special command 'custom' only."
            + "\nRespond with only a valid command phrase or the word 'custom', nothing else.\n"
        )

        await self.world_manager.ai_manager.submit_remote_request(
            self.handle_translation_response,
            person,
            request_type="translation_request",
            prompt=prompt,
            system_message="You are a simulated world command interpreter",
            user_context=user_input,
        )
        return None, None, output

    async def handle_translation_response(
        self, ai_response: str, request_data: str = ""
    ) -> Optional[Tuple[str, str, str]]:
        # Strip any leading/trailing whitespace or carriage returns
        ai_response = ai_response.strip()
        person = request_data["person"]
        output: str = ""
        logger.info("AI translation: %s", ai_response)
        # If the AI translation is 'custom', prompt the person for a custom action
        if ai_response == "custom":
            if not request_data["user_context"]:
                exit(logger, "Custom action requested but no context provided!")
            ai_response += " " + request_data["user_context"]
        if ai_response:
            # Try to process the AI translation as a command, but only try this once
            output = (
                f"\nI think you meant '{ai_response}', and will proceed accordingly.\n"
            )
            command_function, command_args, response_to_person = (
                await self.process_user_input(person, ai_response, translated=True)
            )
            if command_function:
                # Run it
                outcome = await command_function(*command_args)
                return outcome
            elif response_to_person:
                return None, None, response_to_person
            else:
                return None, None, output
        else:
            exit(logger, "AI requester response empty!")

    def check_direction(self, direction: str) -> str:
        if direction not in self.directions:
            return f"'{direction}' is not a valid direction."

    # Get phrases. Each phrase is either a single word, or a number of words in quotes. There can be multiple phrases. Different quotes could be used from one phrase to the next.
    def get_phrases(self, rest_of_response: str) -> List[str]:
        phrases: List[str] = []

        # Regex pattern to match phrases in single or double quotes or unquoted words
        pattern = re.compile(r'(["\'])(.*?)\1|(\S+)')

        # Use findall to get all phrases
        matches = pattern.findall(rest_of_response)

        for match in matches:
            # Match groups: match[1] will contain the quoted phrase, match[2] the unquoted word
            if match[1]:  # This is a quoted phrase
                phrases.append(match[1].strip())
            elif match[2]:  # This is an unquoted word
                phrases.append(match[2].strip())
        return phrases

    # Process person input. Returns a function pointer, a tuple of arguments, and an error message if any.
    async def process_user_input(
        self, person: Person, user_input: str, translated: bool = False
    ) -> Optional[
        Tuple[
            Callable, Union[Tuple[Person, str], Tuple[Person, str, str], Optional[str]]
        ]
    ]:
        person.update_last_action_time()
        if not user_input:
            # Empty command
            return None, None, "You need to enter a command."

        person.add_input_history(f"You: {user_input}")

        # get the rest of the response apart from the first word
        command: str
        rest_of_response: str
        command, rest_of_response = self.parse_user_input(user_input)

        # Check for synonyms
        command = self.synonyms.get(command, command)
        logger.info(f"Command: {command}")

        # Resolve the function associated with a command, and its parameters.
        if command in self.command_functions:
            # Special handling for build command: validate the room name and pass it as an extra parameter, before calling do_build
            if command == "build":

                # First parse the response to get the direction, room name and description. handle the person
                # Using quotes in order to have room names and descriptions with spaces in

                # First take the direction which is one word and must be one of the directions
                direction: str = rest_of_response.split()[0]

                # Check direction is valid and not taken
                outcome: str = self.check_direction(direction)
                if outcome:
                    return None, None, outcome

                # Remove the direction from the response
                rest_of_response: str = " ".join(rest_of_response.split()[1:])
                if not rest_of_response:
                    # User did not specify name of room to build
                    return (
                        None,
                        None,
                        "Please specify room name in quotes and a description.",
                    )

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
                    (person, direction, room_name, room_description),
                    None,
                )
            elif command == "create":
                # First split the response into phrases which are separated by quotes
                phrases = self.get_phrases(rest_of_response)

                # You: create "Big bug" "A big bug that's nice."
                if len(phrases) < 2 or len(phrases) > 3:
                    return (
                        None,
                        None,
                        "Please specify item name and description in quotes, then optional price.",
                    )

                # Check item name is not empty
                item_name: str = phrases[0]

                description: str = phrases[1]

                if len(phrases) == 3:
                    if not phrases[2].isdigit():
                        return None, None, "Price must be a number."
                    price = int(phrases[2])
                else:
                    price = 0

                return (
                    self.command_functions[command]["function"],
                    (person, item_name, description, price),
                    None,
                )
            # Normal command
            return (
                self.command_functions[command]["function"],
                (
                    person,
                    self.strip_outer_quotes(rest_of_response),
                ),
                None,
            )
        # Different return if the command is a direction
        elif command in self.directions:
            return (
                self.world_manager.move_entity,
                (person, command, rest_of_response),
                None,
            )
        elif command == "custom":
            if not rest_of_response:
                exit(logger, "Custom action requested but no context provided!")
            return (
                self.world_manager.do_custom_action,
                (person, rest_of_response),
                None,
            )
        else:
            # If the command is not recognised, try to translate it using AI (unless this is already a translation)
            if not translated:
                outcome = await self.translate_and_process(person, user_input)
                return outcome
            # Invalid command
            return (
                None,
                None,
                (
                    "That is not a recognised command. Available commands:\n"
                    + self.get_commands_description()
                ),
            )
