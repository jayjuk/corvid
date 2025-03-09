from utils import set_up_logger, exit
import asyncio
from typing import Any, Dict, List, Tuple, Optional, Union
import time
import sys
import json

# Set up logger first
logger = set_up_logger()

from world import World
from player import Player
from entity import Entity
from merchant import Merchant
from gameitem import GameItem
from room import Room
from aimanager import AIManager
from storagemanager import StorageManager


class GameManager:
    """Manage the game state and process player input & responses."""

    # Constructor
    def __init__(
        self,
        sio: Any,
        mbh: object,
        storage_manager: StorageManager,
        world_name: str = "jaysgame",
        model_name: Optional[str] = None,
        landscape: Optional[str] = None,
        animals_active: bool = True,
    ) -> None:

        # Static variables
        self.max_inactive_time: int = 300  # 5 minutes
        self.background_loop_active: bool = False
        self.game_loop_time_secs: int = 30  # Animals etc move on this cycle
        self.animals_active: bool = animals_active

        # Set up game state
        self.mbh: object = mbh
        self.sio: Any = sio
        # Register of players currently in the game
        self.players: Dict[str, Player] = {}
        # Register of summon requests
        self.summon_requests: Dict[str, str] = {}

        # Keep a log of all player names including those who have left
        # This is so that when a player disconnects (e.g. closes their browser) after 'quitting' we can
        # understand that, and it will allow them to rejoin with the same name later
        self.player_id_to_name_map: Dict[str, str] = {}

        # General AI manager - disabled in unit tests
        # AI manager is used for the AI to interact with the game
        # Share sio with AI manager in this instance only
        self.ai_manager: Optional[AIManager]
        if model_name:
            self.ai_manager: AIManager = AIManager(
                model_name=model_name, system_message="", mbh=self.mbh
            )
        else:
            self.ai_manager = None
            logger.info("No model name set: AI is disabled.")

        self.world: World = World(
            world_name,
            storage_manager,
            mode=None,
            ai_manager=self.ai_manager,
            landscape=landscape,
        )

        self.item_name_empty_message: str = "Invalid input: item name is empty."

    # All these 'do_' functions are for processing commands from the player.
    # They all take the player item and the rest of the response as arguments,
    # Even if they're not needed. This is to keep the command processing simple.

    async def do_go(self, player: Player, rest_of_response: str) -> str:
        return await self.move_entity(player, rest_of_response, "")

    async def do_push(self, player: Player, rest_of_response: str) -> str:
        item_name: str = self.get_item_name_from_response(rest_of_response)
        if "button" in item_name:
            # Check red button in inventory
            item: Optional[GameItem] = None
            for inv_item in player.get_inventory():
                if item_name.lower() in inv_item.get_name().lower():
                    item = inv_item
                    break
            if item:
                message: str = (
                    f"The Button has been pressed!!! Congratulations to {player.get_name()}!!! The game will restart in 10 seconds..."
                )
                await self.tell_everyone(message)
                for i in range(9, 0, -1):
                    await asyncio.sleep(1)
                    await self.tell_everyone(f"{i}...")
                await asyncio.sleep(1)
                self.create_restart_file()
                await self.mbh.publish("shutdown", message)
                # TODO #15 Restart game without actually restarting the process
                exit(logger, "Game ended by player pushing The Button!")
            else:
                return "You don't have the button in your inventory."
        elif rest_of_response:
            return "You can't push that."
        else:
            return "Push what?"

    def create_restart_file(self) -> None:
        # Temporary flag file checked by the local 'run' script.
        # TODO #15 On the cloud, this will be space junk as the restart is handled by the container service. See above.
        with open("restart.tmp", "w") as f:
            f.write("DELETE ME\n")

    def remove_at_the(self, rest_of_response: str) -> Tuple[str, str]:
        # Strip off at and the
        if rest_of_response and rest_of_response[0:3] == "at ":
            rest_of_response = rest_of_response[3:]
            if rest_of_response[0:4] == "the ":
                rest_of_response = rest_of_response[4:]
            if rest_of_response == "":
                return rest_of_response, "Look at what?"
        return rest_of_response, ""

    def find_item_in_player_inventory(
        self, player: Player, item_name: str
    ) -> Optional[GameItem]:
        """Try to find the item in the player's inventory."""
        for inv_item in player.get_inventory():
            if item_name.lower() in inv_item.get_name().lower():
                return inv_item
        return None

    def find_item_in_merchant_inventory(
        self, player: Player, item_name: str
    ) -> Optional[GameItem]:
        for merchant in self.get_entities("merchant", player.get_current_location()):
            for merchant_item in merchant.get_inventory():
                if item_name and item_name.lower() in merchant_item.get_name().lower():
                    return merchant_item
        return None

    def do_look(self, player: Player, rest_of_response: str) -> str:
        if not rest_of_response:
            # Looking at the room
            message: str = (
                "You look again at the "
                + str(player.get_current_location()).lower()
                + ": "
                + self.world.get_room_description(
                    player.get_current_location(), brief=False, role=player.get_role()
                )
            )
            # Add buildable directions if player is a builder
            if player.role == "builder":
                message += "\n" + self.world.get_room_exits_description(
                    player.get_current_location()
                )
            return message

        # They are looking at something
        rest_of_response, outcome = self.remove_at_the(rest_of_response)
        if outcome:
            return outcome

        # Find what they are looking at
        item_name: str = self.get_item_name_from_response(rest_of_response)
        # Check if the item is in the room
        item = self.world.search_item(item_name, player.get_current_location())
        if not item:
            item = self.find_item_in_player_inventory(player, item_name)
            # Try to find the item in the possession of a merchant
            if not item:
                item = self.find_item_in_merchant_inventory(player, item_name)
        if item:
            return (
                f"You look at {item.get_name(article='the')}: {item.get_description()}"
            )
        # Check if they named an entity
        entity = self.get_entity_by_name(item_name)
        if entity:
            return entity.get_description()
        # If you get here, can't find anything that matches that name
        return f"There is no '{item_name}' here. You can look around (just say look) or look at a specific item."

    async def do_say(
        self, player: Player, rest_of_response: str, shout: bool = False
    ) -> str:
        verb: str = "shouts" if shout else "says"
        # Remove 'to' and player name
        if rest_of_response.startswith("to ") or rest_of_response.startswith("only "):
            return "You can't currently speak to just one person in the room. To converse, just use 'say' followed by what you want to say, everyone in the room will hear you."

        logger.info(f"User {player.name} {verb}: {rest_of_response}")
        mutter_response: str = f"You mutter to yourself, '{rest_of_response}'."
        player_response: str
        if self.get_player_count() == 1:
            player_response = mutter_response
        else:
            told_count: int = await self.tell_others(
                player.player_id, f'{player.name} {verb}, "{rest_of_response}"', shout
            )
            if not told_count:
                player_response = mutter_response
            else:
                player_response = f"You {verb[:-1]}, '{rest_of_response}'."
        return player_response

    async def do_shout(self, player: Player, rest_of_response: str) -> str:
        # Shout is the same as say but to everyone
        outcome = await self.do_say(player, rest_of_response, shout=True)
        return outcome

    async def do_greet(self, player: Player, rest_of_response: str) -> str:
        # Like say hi!
        outcome = await self.do_say(player, "Hi " + rest_of_response)
        return outcome

    def do_wait(self, player: Player, rest_of_response: str) -> str:
        return "You decide to just wait a while."

    async def do_jump(self, player: Player, rest_of_response: str) -> str:
        # Jump to location of another player named in rest_of_response
        other_entity_name: str = rest_of_response
        # find location of other player
        other_entity_location: Optional[str] = self.get_player_location_by_name(
            player.player_id, other_entity_name
        )
        # if found, move player there
        if other_entity_location:
            return await self.move_entity(player, "jump", other_entity_location)
        else:
            return f"'{other_entity_name}' is not a valid player name."

    async def do_shutdown(self, player: Player, rest_of_response: str) -> None:
        message: str = f"{player.name} has triggered a shutdown of the game!"
        if rest_of_response:
            message = message[:-1] + f", saying '{rest_of_response}'."
        logger.info(message)
        await self.tell_everyone(message)
        # TODO #68 Web client should do something when the back end is down, can we terminate the client too?
        # TODO #69 Make shutdown command restart process not shut down
        await self.mbh.publish("shutdown", message)
        await asyncio.sleep(1)
        exit(logger, "Shutdown command invoked by {player.name}")

    async def do_quit(self, player: Player, rest_of_response: str) -> None:
        await self.remove_player(player.player_id, "You have left the game.")

    async def emit_summon_request(self, request_id: str, request: str) -> None:
        emit_data = {"request_id": request_id, "request_data": request}
        await self.mbh.publish("summon_player_request", emit_data)

    async def do_summon(self, player: Player, rest_of_response: str) -> str:
        logger.info(f"Summon command received: {rest_of_response}")
        # Generate a unique request ID from player player_id and time
        request_id: str = player.player_id + str(time.time())
        # Strip quotes from the response
        player_briefing = rest_of_response.strip("'")
        # Trigger a summon request
        self.summon_requests[request_id] = player_briefing
        await self.emit_summon_request(request_id, player_briefing)

    async def do_build(
        self,
        player: Player,
        direction: str,
        room_name: str,
        room_description: Optional[str] = "",
    ) -> str:
        # Create a new room
        if direction in self.world.get_exits(player.get_current_location()):
            return f"There is already a room to the {direction}."

        # Remove 'The ' from the room name
        if room_name.startswith("The "):
            room_name = room_name[4:]

        # Format the room name to be title case
        room_name = room_name.title().replace("'S", "'s")

        # Check and add the room
        response_text, description_prompt, new_grid_reference = (
            self.world.check_room_request(
                player,
                direction,
                room_name,
                room_description,
            )
        )
        # If there was a response, return it
        if response_text:
            return response_text
        # If there is a prompt, submit it to the AI
        if description_prompt:
            await self.ai_manager.submit_remote_request(
                self.handle_room_description_ai_response,
                player,
                "room_description",
                description_prompt,
                player_context={
                    "room_name": room_name,
                    "direction": direction,
                    "current_location": player.get_current_location(),
                    "new_grid_reference": new_grid_reference,
                },
                system_message="You are a helpful AI assistant providing a description for a new location in a game.",
            )
            return "Your room description is being prepared..."
        else:
            response = await self.build_room(
                player,
                player.get_current_location(),
                direction,
                room_name,
                room_description,
                new_grid_reference,
            )
            return response

    async def handle_room_description_ai_response(
        self, ai_response: str, request_data: Dict
    ) -> str:
        player: Player = request_data["player"]
        player_context: Dict = request_data["player_context"]
        room_description: str = ai_response.strip()

        logger.info(f"AI-generated room description: {room_description}")

        # Log the interaction in the AI log
        self.ai_manager.log_response_to_file(player_context, room_description)

        response = await self.build_room(
            player,
            player_context["current_location"],
            player_context["direction"],
            player_context["room_name"],
            room_description,
            player_context["new_grid_reference"],
        )
        return response

    async def build_room(
        self,
        player: Player,
        current_location: str,
        direction: str,
        room_name: str,
        room_description: str,
        new_grid_reference,
    ) -> str:

        # If there was no response, it means room was built directly - handle the room built
        self.world.add_room(
            player,
            current_location,
            direction,
            room_name,
            room_description,
            new_grid_reference,
        )

        # Otherwise, tell other players about the new room
        await self.tell_others(
            player.player_id,
            f"{player.name} has built to the {direction} and made a new location, {room_name}.",
            shout=True,
        )

        # Emit event to trigger a room image creation
        await self.request_room_image_creation(room_name, room_description)

        # If this is the first room apart from the empty world room, move all players there
        return_message = f"You build {direction} and make a new location, {room_name}: {room_description}."
        if self.world.is_empty:
            logger.info(
                "This is the first room in the world. Removing the starting room."
            )
            for other_player in self.players.values():
                await self.move_entity(other_player, "join", room_name)
            # Move self
            await self.move_entity(player, "join", room_name)

            # Update the world to reflect that it is no longer empty
            self.world.is_empty = False
            # Remove the empty world room
            self.world.delete_room(current_location)
            return_message += " Congratulations, it is the first location in this world! You move there immediately."

        return return_message

    async def request_room_image_creation(
        self, room_name: str, room_description: str
    ) -> None:
        logger.info(f"Requesting image creation for room {room_name}")
        # Emit event to trigger a room image creation
        await self.mbh.publish(
            "image_creation_request",
            {
                "world_name": self.world.name,
                "room_name": room_name,
                "description": room_description,
                "landscape": self.world.landscape,
            },
        )

    # Create item
    def do_create(
        self, player: Player, item_name: str, description: str, price: int = 0
    ) -> str:

        # Strip trailing non alphabet characters from item name
        item_name = item_name.rstrip(".,!?")

        # Check the item name is valid - alphabet characters and spaces only
        if not all(c.isalpha() or c.isspace() for c in item_name):
            return "Invalid input: item name must contain only letters and spaces."

        # Check the item name is valid
        if item_name == "":
            return self.item_name_empty_message

        # Check the price is valid
        MAX_PRICE = 1000
        if price < 0:
            return "Invalid input: price cannot be negative."
        elif price > MAX_PRICE:
            return f"Invalid input: price must be less than {MAX_PRICE}."

        # Check if the item is in the room
        item: Optional[GameItem] = self.world.search_item(
            item_name, player.get_current_location(), exact_match=True
        )
        if item:
            return f"{item.get_name(article='The')} is already here."
        # Check if they named an entity
        elif self.get_entity_by_name(item_name):
            return f"{item_name} is already the name of an entity."
        # Create the item
        # Add a full stop to the end of the description if it is missing
        if description[-1] != ".":
            description += "."
        outcome: Optional[str] = self.world.create_item(
            item_name, description, price, player.get_current_location()
        )
        if outcome:
            return outcome
        return f"You create {item_name} with the following description: {description}"

    # Function to parse rest of response and return a list, each item in the list is either one word or a single quoted phrase
    def parse_rest_of_response(self, rest_of_response: str) -> List[str]:
        logger.info(f"Parsing rest of response: {rest_of_response}")

        # Split the response into words
        response_list: List[str] = rest_of_response.split()
        # Loop through the words and combine single quoted phrases
        combined_list: List[str] = []
        combined_phrase: str = ""
        for word in response_list:
            if word[0] == "'":
                combined_phrase = word[1:]
            elif word[-1] == "'":
                combined_phrase += " " + word[:-1]
                combined_list.append(combined_phrase)
                combined_phrase = ""
            elif combined_phrase:
                combined_phrase += " " + word
            else:
                combined_list.append(word)

        logger.info(f"Parsed response: {combined_list}")
        return combined_list

    # Spawn an animal
    def do_spawn(self, player: Player, rest_of_response: str) -> str:
        # Get the description and actions from the rest of the response
        animal_name: str
        description: str
        list_of_actions: str
        inputs_list = self.parse_rest_of_response(rest_of_response)
        if len(inputs_list) == 3:
            # Split the response into description and actions
            animal_name, description, list_of_actions = inputs_list
        else:
            return "You need to provide a name, description and actions for the animal."

        # Check the animal name is valid
        if animal_name == "":
            return "Invalid input: animal name is empty."

        # Check if the animal is in the room
        animal: Optional[Entity] = self.get_entity_by_name(animal_name)
        if animal:
            return f"{animal_name} is already here."
        # Check if they named an item
        elif self.world.search_item(animal_name, player.get_current_location()):
            return f"{animal_name} is already the name of an item."

        # Check list of actions is valid
        if list_of_actions and list_of_actions.isdigit():
            return "Invalid input: list of actions cannot be a number. Were you trying to create an item? If so, use command 'create' instead."

        # Spawn the animal using same dictionary as per the world file
        entity_dict = {
            "name": animal_name,
            "type": "animal",
            "description": description,
            "location": player.get_current_location(),
            "actions": list_of_actions.split(","),
            "inventory": [],
            "action_chance": 0.1,
            "move_chance": 0,  # For now, animals created by players don't move
        }
        outcome: Optional[str] = self.world.spawn_entity(entity_dict)
        if outcome:
            return outcome
        return f"You spawn a {animal_name}: {description}."

    # Check if an item is an entity
    def get_entity_by_name(self, item_name: str) -> Optional["Entity"]:
        if item_name:
            for other_entity in self.get_other_entities():
                if (
                    str(other_entity.name).lower() == str(item_name).lower()
                    or other_entity.get_role() == item_name.lower()
                ):
                    return other_entity
        return None

    # Get entities of a certain type
    def get_entities(
        self, entity_type: str, room: Optional[Room] = None
    ) -> List[Entity]:
        # Merchants are entities of a certain type.
        # If a room is specified, only return merchants in that room
        merchants = []
        for entity in self.world.entities.values():
            if entity.get_role() == entity_type:
                if room is None or entity.get_current_location() == room:
                    merchants.append(entity)
        return merchants

    # Sale transaction
    def transact_sale(self, item_name: str, player: Player, merchant: Merchant) -> str:
        for item in player.get_inventory():
            if item.get_name().lower() == item_name.lower():
                # Change item ownership
                transfer_outcome: str = item.transfer(player, merchant)
                if not transfer_outcome:
                    # Add the money to the player's inventory
                    player.add_money(item.get_price())
                    # NOTE: Merchant has unlimited money for now at least
                    return f"You sell {item.get_name(article='the')} to {merchant.get_name()} for {self.world.get_currency(item.get_price())}."
                else:
                    return "The sale fell through: " + transfer_outcome
        return f"'{item_name}' is not in your inventory."

    async def make_purchase(
        self, item: GameItem, player: Player, merchant: Merchant
    ) -> str:
        # Simply return True if the item is in the merchant's possession and the player said to buy
        if player.deduct_money(item.get_price()):
            transfer_issue = item.transfer(merchant, player)
            if transfer_issue:
                return transfer_issue
            # If no issue, tell the others about the transaction
            await self.tell_others(
                player.player_id,
                f"{player.name} has bought {item.get_name(article='the')} from {merchant.get_name()}.",
            )
            return f"Congratulations, you successfully purchased {item.get_name(article='the')} for {self.world.get_currency(item.get_price())}."

        return f"You do not have enough money to buy {item.get_name(article='the')}."

    async def transact_buy_get(
        self, action: str, item_name: str, player: Player, merchant: Merchant
    ) -> str:
        found_count: int = 0
        for item in merchant.get_inventory():
            if (
                item_name.lower() in item.get_name().lower()
                or item_name.lower() == "all"
            ):
                found_count += 1
                if action == "get":
                    # Simply return True if the item is in the merchant's possession and the player said to get not buy
                    # As we can't assume they were willing to buy it
                    return f"The item '{item.get_name()}' is in the possession of a merchant. Perhaps you can purchase it?"
                elif action == "buy":
                    outcome: str = await self.make_purchase(item, player, merchant)
                    return outcome
        if found_count == 0:
            return f"There is no {item_name} to be found here."

    # Check if an item is in a merchant's possession
    async def transact_item(
        self, item_name: str, player: Player, action: str = "get"
    ) -> str:
        merchants = self.get_entities("merchant", player.get_current_location())
        if action in ("buy", "sell") and not merchants:
            return "There is no merchant here to trade with."

        # Try each merchant in the room
        for merchant in merchants:
            if action == "sell":
                return self.transact_sale(item_name, player, merchant)
            else:
                # Don't go any further if pockets are full!
                if not player.can_add_item():
                    return "You can't carry any more."
                outcome: str = await self.transact_buy_get(
                    action, item_name, player, merchant
                )
                return outcome
        # If we get here, the item is not in any merchant's possession
        return f"You are unable to {action} '{item_name}' here."

    # Get / pick up an item
    async def do_get(self, player: Player, rest_of_response: str) -> str:
        logger.info("Doing get command.")
        # First check in case they wrote 'pick up'. If so, remove the 'up'.
        if rest_of_response.startswith("up "):
            rest_of_response = rest_of_response[3:]
        # TODO #70 If in future pick is a verb e.g. pick a lock, select, we will need to pass the original verb into the functions

        # Get item name by calling a function to parse the response
        item_name: str = self.get_item_name_from_response(rest_of_response)

        # Check the item name is valid
        if item_name == "":
            return self.item_name_empty_message

        # Loop to handle wild cards
        keep_looking: bool = True
        found: bool = False
        while keep_looking:
            keep_looking = False
            # Check if the item is in the room
            item: Optional[GameItem] = self.world.search_item(
                item_name, player.get_current_location()
            )
            if item:
                found = True
                # Setting player will remove the item from the room
                result: Optional[str] = item.set_possession(player)
                if not result:
                    await self.tell_player(
                        player, f"You pick up {item.get_name(article='the')}."
                    )
                    # Only repeat if something found
                    keep_looking = True
                else:
                    return result
            # Check if they named an entity
            elif self.get_entity_by_name(item_name):
                return f"I would advise against picking up {item_name}, they will not react well!"
            # Check if the item is in the possession of a merchant
            elif item_name != "all" and not found:
                outcome: Optional[str] = await self.transact_item(
                    item_name, player, "get"
                )
                if outcome:
                    return outcome
                return f"There is no {item_name} to be found here."
        if not found:
            return "There is nothing here that you can pick up."

    def do_inventory(self, player: Player, rest_of_response: str) -> str:
        # Not used, next line is to avoid warnings
        return player.get_inventory_description()

    def get_item_list_text(self, items: List[GameItem]) -> str:
        drop_list_text: str = ""
        drop_count: int = 0
        for item in items:
            drop_count += 1
            if drop_count > 1:
                if drop_count == len(items):
                    drop_list_text += " and "
                else:
                    drop_list_text += ", "
            drop_list_text += f"{item.get_name(article='the')}"
        drop_list_text += "."
        return drop_list_text

    async def do_drop(self, player: Player, rest_of_response: str) -> str:
        # Get item name by calling a function to parse the response
        item_name: str = self.get_item_name_from_response(rest_of_response)

        # Check the item name is valid
        if item_name == "":
            return self.item_name_empty_message
        if (
            self.world.get_currency(amount=None, short=False, plural=True) in item_name
            or self.world.get_currency(amount=None, short=False, plural=False)
            in item_name
        ):
            return "You can't drop your money, you might need it!"
        # Check if the item is in the player's inventory, if so, drop it
        # "all" is a special case to drop everything
        items: List[GameItem] = player.drop_items(item_name)
        if items:
            drop_list_text: str = self.get_item_list_text(items)
            # Tell the others about the drop
            await self.tell_others(
                player.player_id,
                f"{player.name} has dropped {drop_list_text}",
            )
            return "You drop " + drop_list_text
        else:
            if item_name == "all":
                return "You are not carrying anything."
            else:
                return f"You are not carrying '{item_name}'."

    async def do_buy(self, player: Player, rest_of_response: str) -> str:
        # Get item name by calling a function to parse the response
        item_name: str = self.get_item_name_from_response(rest_of_response)

        # Check the item name is valid
        if item_name == "":
            return self.item_name_empty_message

        # Check if the item is in the room
        item: Optional[GameItem] = self.world.search_item(
            item_name, player.get_current_location()
        )
        if item:
            # Can just pick it up
            return "You don't have to buy that, you can just pick it up!"
        # Check if they named an entity
        elif self.get_entity_by_name(item_name):
            return f"That {item_name} is not for sale!"
        # Otherwise proceed to try to buy it
        outcome: str = await self.transact_item(item_name, player, "buy")
        return outcome

    async def do_sell(self, player: Player, rest_of_response: str) -> str:
        # Get item name by calling a function to parse the response
        item_name: str = self.get_item_name_from_response(rest_of_response)
        # Check the item name is valid
        if item_name == "":
            return self.item_name_empty_message
        if (
            self.world.get_currency(amount=None, short=False, plural=True) in item_name
            or self.world.get_currency(amount=None, short=False, plural=False)
            in item_name
        ):
            return "You can't sell money!"

        # Check if the item is in the player's inventory
        found_count: int = 0
        tmp_inv: List[GameItem] = player.get_inventory().copy()
        for item in tmp_inv:
            if (
                item_name.lower() in item.get_name().lower()
                or item_name.lower() == "all"
            ):
                found_count += 1
                if not item.get_price():
                    return f"You can't sell {item.get_name(article='the')} - it is valueless (or priceless!)."
                # Try to sell it to a merchant
                outcome: str = await self.transact_item(item.get_name(), player, "sell")
                await self.tell_player(player, outcome)
        if item_name != "all" and found_count == 0:
            return f"You are not carrying '{item_name}'."

    def do_trade(self, player: Player, rest_of_response: str) -> str:
        # TODO #71 Implement trade command
        return "Support for this command coming soon!"

    def do_attack(self, player: Player, rest_of_response: str) -> str:
        return "This game does not condone violence! There must be another way to achieve your goal..."

    # Evaluate and if appropriate perform a custom action, which can modify the state of the location
    # And objects / entities in the vicinity
    async def do_custom_action(self, player: Player, action: str) -> str:
        logger.info("About to do a custom action: " + action)
        # Get the AI to figure out the impact on nearby things from this action
        prompt = (
            f"The player in a game is in location {player.get_current_location()} "
            + f" which has current description '{self.world.rooms[player.get_current_location()].description}'."
        )
        # Check if player has inventory
        if player.get_inventory():
            prompt += f" The player has the following items in their inventory: {player.get_inventory_description()}"
        # Check for any objects in this location
        prompt += f" {self.world.get_room_items_description(player.get_current_location(), detail=True):}"
        # Check for any entities in this location
        for other_entity in self.get_other_entities(player.player_id):
            if other_entity.get_current_location() == player.get_current_location():
                prompt += (
                    f" {other_entity.get_name().capitalize()} is here: "
                    + other_entity.get_description()
                    + "\n"
                )

        prompt += (
            f"\nThe player issues this command: {action}"
            + "\nRespond with a JSON object as follows:"
            + "\nIf this makes sense (try to be creative flexible and permissive, allowing some artistic license), respond with feedback to the player in string property 'success_response' and any combination (or none) of the following:"
            + "\n* Something the player says (only if appropriate) in string property 'player_utterance'."
            + "\n* The updated description of the current location in string property 'updated_location'."
            + "\n* The updated descriptions of any modified items (only those listed earlier) as nested object property 'updated_items', with item names as keys and new descriptions as values."
            + "\n* The descriptions of any newly created items as nested object property 'new_items', with new item names as keys and descriptions as values."
            + "\n* The descriptions of any destroyed/deleted items as string array 'deleted_items'."
            + " (If an item has changed so much that its name no longer applies, then delete it and replace it with one or more new items. Note that an item cannot be both updated and deleted.)"
            + "\n* The updated descriptions of any modified entities (only those listed earlier) as nested object property 'updated_entities', with entity names as keys and new descriptions as values."
            + "\nOnly include the updated elements if they have changed in a way that another player who did not witness the cause of the change would notice."
            + "\n If the command doesn't make sense or is too unrealistic, provide a meaningful response in JSON with element 'rejection_response'."
        )
        await self.ai_manager.submit_remote_request(
            self.handle_custom_action_response,
            player,
            "custom_action",
            prompt,
            system_message="You are an AI assistant helping to evaluate a custom action in a game.",
        )

    async def handle_custom_action_response(
        self, ai_response: str, request_data: str = ""
    ) -> str:
        player: Player = request_data["player"]
        player_context: str = request_data["player_context"]
        try:
            response_json = json.loads(ai_response)
        except json.JSONDecodeError:
            logger.error(
                f"AI response to '{player_context}' was not valid JSON: {ai_response}"
            )
            return f"The AI could not understand the command '{player_context}'."
        # If a list comes back, take the first element
        if isinstance(response_json, list):
            if len(response_json) == 1:
                response_json = response_json[0]
            else:
                logger.error(
                    f"AI response to '{player_context}' was a list: {response_json}"
                )
                return "The AI gave an invalid response to '{player_context}'."
        if not isinstance(response_json, dict):
            logger.error(
                f"AI response to '{player_context}' was not a dictionary: {response_json}"
            )
            return "The AI gave an invalid response to '{player_context}'."
        if response_json.get("success_response"):
            logger.info(
                f"AI understood the command '{player_context}' and returned a success response: {response_json.get('success_response')}"
            )
            return_text: str = response_json.get("success_response")
            if response_json.get("player_utterance"):
                if return_text:
                    return_text += " "
                return_text += await self.do_say(
                    player, response_json["player_utterance"]
                )
            if response_json.get("updated_location"):
                self.world.update_room_description(
                    player.get_current_location(), response_json["updated_location"]
                )
            if response_json.get("updated_entities"):
                for entity_name, new_description in response_json[
                    "updated_entities"
                ].items():
                    entity = self.get_entity_by_name(entity_name)
                    if entity:
                        self.world.update_entity_description(entity, new_description)
            if response_json.get("updated_items"):
                for item_name, new_description in response_json[
                    "updated_items"
                ].items():
                    item = self.world.search_item(
                        item_name, player.get_current_location()
                    )
                    if item:
                        self.world.update_item_description(item, new_description)
            if response_json.get("deleted_items"):
                for item_name in response_json["deleted_items"]:
                    self.world.delete_item(item_name, player)
            if response_json.get("new_items"):
                for item_name, new_description in response_json["new_items"].items():
                    # Create item
                    outcome: Optional[str] = self.world.create_item(
                        item_name,
                        new_description,
                        price=None,
                        location=player.get_current_location(),
                    )
                    # If there is an issue, return it
                    # TODO #91 Handle errors in custom actions better
                    if outcome:
                        return outcome
            return return_text

        elif "rejection_response" in response_json:
            return response_json["rejection_response"]
        exit(
            logger,
            "The AI did not manage to respond as instructed with success or rejection response!",
        )

    # End of 'do_' functions

    # Getters

    # Parse item name from the response after the initial verb that triggered the function
    def get_item_name_from_response(self, rest_of_response: str) -> str:
        if rest_of_response == "everything" or rest_of_response == "*":
            return "all"

        if rest_of_response.startswith(" from "):
            rest_of_response = rest_of_response[6:]

        # This is now simple because quotes are stripped out earlier
        return rest_of_response

    # Get a description of the players in the game
    def get_players_text(self) -> str:
        others_count: int = self.get_player_count()
        if others_count == 0:
            return "You are the first player to join the game.\n"
        elif others_count == 1:
            return "You are the second player in the game.\n"
        else:
            return f"There are {others_count} other players in the game.\n"

    # Get location of player given a name
    def get_player_location_by_name(
        self, player_id: str, player_name: str
    ) -> Optional[str]:
        for other_entity in self.get_other_entities(player_id):
            if str(other_entity.name).lower() == str(player_name).lower():
                return other_entity.get_current_location()
        return None

    # Get number of players in the game
    def get_player_count(self) -> int:
        return len(self.players)

    # Check if a player name is unique
    def is_existing_player_name(self, player_name: str) -> bool:
        for player_id, player in self.players.items():
            if str(player.name).lower() == str(player_name).lower():
                return True
        return False

    # End of getters

    # Setters etc

    # Process player setup request from client
    async def process_player_setup(
        self, player_id: str, player_info: Dict[str, Any], help_message: str
    ) -> Union[Tuple[str, str], None]:
        # Be defensive as this is coming from either UI or AI broker
        if "name" not in player_info:
            logger.error("FATAL: Player name not specified")
            sys.exit()

        # Strip out any whitespace (defensive in case of client bug)
        player_name: str = player_info["name"].strip().title()

        # Check uniqueness here, other checks are done in the player class
        if self.is_existing_player_name(player_name):
            # Issue with player name setting
            return f"The name {player_name} is already in use."
        if player_name == "system":
            # Do not let any player be called system
            return (
                "The name '{player_name}' is a reserved word, it would be confusing to be called that.",
            )

        # Create/load the player, who is part of the world like entities items etc
        outcome: Union[Tuple[str, str], None]
        player_info: Union[Player, None]
        outcome, player_info = self.world.create_player(
            player_id, player_name, player_info.get("role")
        )
        # Outcomes are adverse
        if outcome:
            return outcome

        # Register this player with the game server
        self.register_player(player_id, player_info, player_name)

        # Tell other players about this new player
        await self.tell_others(
            player_id,
            f"{player_name} has joined the game, starting in the {player_info.get_current_location()}; there are now {self.get_player_count()} players.",
            shout=True,
        )

        # Tell this player about the game
        instructions: str = (
            f"Welcome to the game, {player_name}. "
            + self.list_players(player_id)
            + " "
            + help_message
        )

        await self.tell_player(player_info, instructions, type="instructions")

        await self.tell_player(
            player_info,
            await self.move_entity(
                player_info, "join", player_info.get_current_location()
            ),
        )

        await self.emit_game_data_update()

        # Spawn the world-wide metadata loop when the first player is created
        # This is to minimise resource usage when no one is playing.
        await self.activate_background_loop()

    def list_players(self, player_id: str) -> str:
        if self.get_player_count() == 1:
            return "You are currently the only player in the game."
        player_list = "Other players in the game: "
        for other_player_id, player_name in self.player_id_to_name_map.items():
            if other_player_id != player_id:
                player_list += player_name + ", "
        player_list = player_list[:-2] + "."
        return player_list

    # Build move message back to player
    def build_move_outcome_message(
        self, player: Player, action: str, next_room: str
    ) -> str:
        # Build message. only describe room if it is new to this player.
        message = f"You {action} the {next_room.lower()}"
        if next_room in player.seen_rooms:
            message += f". {self.world.get_room_description(next_room, brief=True, role=player.get_role())}"
        else:
            message += f": {self.world.get_room_description(next_room, role=player.get_role())}"
            # Check for other entities who are already where you are arriving.
        logger.info(f"Checking for other entities than {player.player_id}")
        for other_entity in self.get_other_entities(player.player_id):
            if other_entity.get_current_location() == next_room:
                message += f" {other_entity.get_name().capitalize()} is here."
                if other_entity.get_role() == "merchant":
                    message += " " + other_entity.get_inventory_description()
        return message

    # Resolve move action
    def resolve_move_action(self, direction: str) -> str:
        if direction == "jump":
            return "jump to"
        if direction == "join":
            return "start in"
        return f"head {direction} to"

    async def move_entity(
        self, entity: Entity, direction: str, next_room: Optional[str] = None
    ) -> str:
        # Set new room
        previous_room: str = entity.get_current_location()

        # Resolve arrival and departure messages
        departure_message: str
        arrival_message: str
        if direction == "jump":
            departure_message = f"{entity.name} has disappeared in a puff of smoke!"
            arrival_message = f"{entity.name} has materialised as if by magic!"
        elif direction == "join":
            departure_message = ""
            arrival_message = ""  # Covered elsewhere
        elif direction in self.world.get_exits(entity.get_current_location()):
            next_room = self.world.get_next_room(
                entity.get_current_location(), direction
            )
            their_name: str = entity.name
            # Describe animals with 'the' when they leave, 'a' when they arrive
            if entity.get_role() == "animal":
                their_name = entity.get_name(article_type="definite").capitalize()
            departure_message = f"{their_name} leaves, heading {direction} to the {str(next_room).lower()}."
            their_name = entity.name
            if entity.get_role() == "animal":
                their_name = entity.get_name(article_type="indefinite").capitalize()
            arrival_message = f"{their_name} arrives from the {previous_room.lower()}."
        elif direction in self.world.get_directions():
            # Valid direction but no exit
            return f"You can't go {direction}." + self.world.get_room_exits_description(
                entity.get_current_location()
            )
        else:
            # Not a valid direction

            # First check in case a room is mentioned
            # Loop through the exits to see if any of them match the room name
            for exit_dir, exit_room in self.world.rooms[
                entity.get_current_location()
            ].exits.items():
                if exit_room.lower() in direction.lower():
                    return await self.move_entity(entity, exit_dir)

            return (
                f"{direction} is not a valid direction or room name. "
                + self.world.get_room_exits_description(entity.get_current_location())
            )

        # Check for other players you are leaving / joining
        for other_entity in self.get_other_entities(
            entity.player_id, players_only=True
        ):
            if other_entity.get_current_location() == entity.get_current_location():
                await self.tell_player(
                    other_entity,
                    departure_message,
                )
            elif other_entity.get_current_location() == next_room:
                await self.tell_player(
                    other_entity,
                    arrival_message,
                )

        message: str = ""
        if entity.is_player:
            message = self.build_move_outcome_message(
                entity, self.resolve_move_action(direction), next_room
            )
            # Emit update to player
            await self.emit_player_room_update(entity, next_room)

        # Set new room
        entity.set_location(next_room)

        return message

    def register_player(
        self, player_id: str, player: Player, player_name: str
    ) -> Player:
        self.players[player_id] = player
        self.player_id_to_name_map[player_id] = player_name
        return player

    # Emit a message about a room to a specific player
    async def emit_player_room_update(self, player: Player, room: str) -> None:
        # Tell the player about the room including the image name
        await self.mbh.publish(
            "room_update",
            {
                "image": self.world.get_room_image_url(room),
                "title": room,
                "description": self.world.get_room_description(
                    room,
                    brief=False,
                    role=player.get_role(),
                    show_items=False,
                    show_exits=False,
                ),
                "exits": self.world.get_room_exits_description(room),
            },
            player.player_id,
        )

    # Emit a message to all players
    async def tell_everyone(self, message: str) -> None:
        await self.tell_others(None, message, shout=True)

    # Emit a message to all players except the one specified
    async def tell_others(
        self, player_id: Optional[str], message: str, shout: bool = False
    ) -> int:
        told_count = 0
        if message.strip():
            for other_player_id, other_player in self.players.items():
                # Only tell another player if they are in the same room
                if player_id != other_player_id and (
                    shout
                    or other_player.get_current_location()
                    == self.players[player_id].get_current_location()
                ):
                    await self.tell_player(other_player, message)
                    told_count += 1
        return told_count

    # Emit a message to a specific player
    async def tell_player(
        self, player: Player, message: str, type: str = "game_update"
    ) -> None:
        message = message.strip()
        if message:
            await self.mbh.publish(type, message, player.player_id)
            player.add_input_history(f"Game: {message}")

    # Get other entities
    def get_other_entities(
        self, player_id: Optional[str] = None, players_only: bool = False
    ) -> List[Union[Player, Entity]]:
        other_entities: List[Union[Player, Entity]] = []
        for other_player_id, other_player in self.players.items():
            if player_id is None or player_id != other_player_id:
                other_entities.append(other_player)
        if not players_only:
            for entity in self.world.entities.values():
                # Check if not player
                if not isinstance(entity, Player):
                    other_entities.append(entity)
        return other_entities

    # Emit game data update to all players
    async def emit_game_data_update(self) -> None:
        if self.get_player_count() > 0:
            game_data: Dict[str, int] = {"player_count": self.get_player_count()}
            await self.mbh.publish(
                "game_data_update",
                game_data,
            )

    # Check each player to see if they have been inactive for too long
    async def check_players_activity(self) -> None:
        current_time: float = time.time()
        player_ids_to_remove: List[str] = []
        # First go through players and make a list of who to remove
        for player_id, player in self.players.items():
            if current_time - player.last_action_time > self.max_inactive_time:
                player_ids_to_remove.append(player_id)
        # Then once you're out of that dictionary, remove them
        for player_id in player_ids_to_remove:
            await self.remove_player(
                player_id, "You have been logged out due to inactivity."
            )

    # Remove a player from the game
    async def remove_player(self, player_id: str, reason: str) -> None:
        if player_id in self.players:
            player = self.players[player_id]
            # Make player drop all items in their inventory
            drop_outcome: str = await self.do_drop(player, "all")
            await self.tell_player(player, drop_outcome)
            # TODO #6 Create coin items corresponding to their money
            await self.tell_player(
                player,
                reason,
            )
            message: str = (
                f"{player.name} has left the game; there are now {self.get_player_count()-1} players."
            )
            logger.info(message)
            await self.tell_others(
                player_id,
                message,
                shout=True,
            )
            await self.emit_game_data_update()
            # Give player time to read the messages before logging them out
            await asyncio.sleep(3)
            await self.mbh.publish("logout", reason, player_id)
            # Check again (race condition)
            if player_id in self.players:
                del self.players[player_id]
            # If there are no players left, stop the background loop
            if self.get_player_count() == 0:
                self.deactivate_background_loop()
        else:
            logger.info(
                f"Player with player_id {player_id} ({self.player_id_to_name_map.get(player_id,'name unknown')}) has already been removed, they probably quit before."
            )

    # Process image creation response from AI image generator
    async def process_image_creation_response(
        self, room_name: str, image_filename: str, success: str
    ) -> None:
        logger.info(f"Image creation response for {room_name}: {success}")
        if success:
            self.world.update_room_image(room_name, image_filename)
            await self.tell_everyone(f"Room image for {room_name} has been created.")
        else:
            await self.tell_everyone(
                f"Room image creation for {room_name} failed: {image_filename}"
            )

    # Process summon player response from player manager
    async def process_summon_player_response(self, request_id: str) -> None:
        if request_id in self.summon_requests:
            await self.tell_everyone(
                f"Player {self.summon_requests[request_id]['player_name']} has been summoned!"
            )
            logger.info(f"Removing summon request {request_id}")
            del self.summon_requests[request_id]

    # Spawn the world-wide metadata loop when the first player is created
    async def activate_background_loop(self) -> None:
        if not self.background_loop_active:
            logger.info("Activating background loop.")
            self.background_loop_active = True
            asyncio.create_task(self.game_background_loop())

    # Cause the game background loop to exit
    def deactivate_background_loop(self) -> None:
        logger.info("Deactivating background loop.")
        self.background_loop_active = False

    # This loop runs in the background to do things like broadcast player count
    # It only runs when there are players in the game
    async def game_background_loop(self) -> None:
        while self.background_loop_active:
            # Run the loop periodically
            await asyncio.sleep(self.game_loop_time_secs)

            # Time out players who do nothing for too long.
            await self.check_players_activity()

            # Move animals around
            if self.animals_active:
                direction: str
                for animal in self.get_entities("animal"):
                    direction = animal.maybe_pick_direction_to_move()
                    if direction:
                        logger.info(f"Moving {animal.name} {direction}")
                        await self.move_entity(animal, direction)
                    else:
                        gesture_description: str = animal.maybe_gesture()
                        if gesture_description:
                            logger.info(
                                f"{animal.name} will gesture {gesture_description}"
                            )
                            # Check for other players who will witness the gesture
                            for other_entity in self.get_other_entities(
                                None, players_only=True
                            ):
                                if (
                                    other_entity.get_current_location()
                                    == animal.get_current_location()
                                ):
                                    await self.tell_player(
                                        other_entity,
                                        gesture_description,
                                    )
