from logger import setup_logger, exit

# Set up logger first
logger = setup_logger()

from typing import Any, Dict, List, Tuple, Optional, Union
import eventlet
import time
import sys
from world import World
from player import Player
from entity import Entity
from merchant import Merchant
from gameitem import GameItem
from room import Room
from aimanager import AIManager
from storagemanager import StorageManager
import json


class GameManager:
    """Manage the game state and process player input & responses."""

    # Constructor
    def __init__(
        self,
        sio: str,
        storage_manager: StorageManager,
        world_name: str = "jaysgame",
        model_name: str = None,
        image_model_name: str = None,
    ) -> None:

        # Static variables
        self.max_inactive_time: int = 300  # 5 minutes
        self.background_loop_active: bool = False
        self.game_loop_time_secs: int = 30  # Animals etc move on this cycle

        # Set up game state
        self.sio: str = sio
        # Register of players currently in the game
        self.players: Dict[str, Player] = {}
        # Keep a log of all player names including those who have left
        # This is so that when a player disconnects (e.g. closes their browser) after 'quitting' we can
        # understand that, and it will allow them to rejoin with the same name later
        self.player_sid_to_name_map: Dict[str, str] = {}

        # General AI manager - disabled in unit tests
        self.ai_manager: Optional[AIManager]
        if model_name:
            self.ai_manager: AIManager = AIManager(model_name=model_name)
        else:
            self.ai_manager = None
            logger.info("No model name set: AI is disabled.")

        self.world: World = World(
            world_name,
            storage_manager,
            mode=None,
            image_model_name=image_model_name,
        )

        self.item_name_empty_message: str = "Invalid input: item name is empty."

    # All these 'do_' functions are for processing commands from the player.
    # They all take the player item and the rest of the response as arguments,
    # Even if they're not needed. This is to keep the command processing simple.

    def do_go(self, player: Player, rest_of_response: str) -> str:
        return self.move_entity(player, rest_of_response, "")

    def do_push(self, player: Player, rest_of_response: str) -> None:
        item_name: str = self.get_item_name_from_response(rest_of_response)
        if "button" in item_name:
            # Check red button in inventory
            item: Optional[GameItem]
            for inv_item in player.get_inventory():
                if item_name.lower() in inv_item.get_name().lower():
                    item = inv_item
                    break
            if item:
                message: str = (
                    f"The Button has been pressed!!! Congratulations to {player.get_name()}!!! The game will restart in 10 seconds..."
                )
                self.tell_everyone(message)
                for i in range(9, 0, -1):
                    eventlet.sleep(1)
                    self.tell_everyone(f"{i}...")
                eventlet.sleep(1)
                self.create_restart_file()
                self.sio.emit("shutdown", message)
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
        return f"There is no '{item_name}' here."

    def do_say(self, player: Player, rest_of_response: str, shout: bool = False) -> str:
        verb: str = "shouts" if shout else "says"
        # Remove 'to' and player name
        if rest_of_response.startswith("to "):
            return "You can't currently speak to just one person in the room. To converse, just use 'say' followed by what you want to say, everyone in the room will hear you."

        logger.info(f"User {player.name} {verb}: {rest_of_response}")
        player_response: str
        if self.get_player_count() == 1:
            player_response = "You are the only player in the game currently!"
        else:
            told_count: int = self.tell_others(
                player.sid, f'{player.name} {verb}, "{rest_of_response}"', shout
            )
            if not told_count:
                player_response = "There is no one else here to hear you!"
            else:
                player_response = f"You {verb[:-1]}, '{rest_of_response}'."
        return player_response

    def do_shout(self, player: Player, rest_of_response: str) -> str:
        # Shout is the same as say but to everyone
        return self.do_say(player, rest_of_response, shout=True)

    def do_greet(self, player: Player, rest_of_response: str) -> str:
        # Like say hi!
        return self.do_say(player, "Hi " + rest_of_response)

    def do_wait(self, player: Player, rest_of_response: str) -> str:
        return "You decide to just wait a while."

    def do_jump(self, player: Player, rest_of_response: str) -> str:
        # Jump to location of another player named in rest_of_response
        other_entity_name: str = rest_of_response
        # find location of other player
        other_entity_location: Optional[str] = self.get_player_location_by_name(
            player.sid, other_entity_name
        )
        # if found, move player there
        if other_entity_location:
            return self.move_entity(player, "jump", other_entity_location)
        else:
            return f"'{other_entity_name}' is not a valid player name."

    def do_shutdown(self, player: Player, rest_of_response: str) -> None:
        message: str = f"{player.name} has shut down the server."
        if rest_of_response:
            message = message[:-1] + f", saying '{rest_of_response}'."
        logger.info(message)
        self.tell_everyone(message)
        # TODO #68 Web client should do something when the back end is down, can we terminate the client too?
        # TODO #69 Make shutdown command restart process not shut down
        self.sio.emit("shutdown", message)
        eventlet.sleep(1)
        exit(logger, "Shutdown command invoked")

    def do_quit(self, player: Player, rest_of_response: str) -> None:
        self.remove_player(player.sid, "You have left the game.")

    def do_build(
        self,
        player: Player,
        direction: str,
        room_name: str,
        room_description: Optional[str],
    ) -> str:
        # Create a new room
        if direction in self.world.get_exits(player.get_current_location()):
            return f"There is already a room to the {direction}."

        # If player does not provide a room description, try to get one from the AI
        if not room_description:
            # Get existing room descriptions into a list for inspiration
            existing_room_descriptions: List[str] = [
                self.world.rooms[room].description for room in self.world.rooms.keys()
            ]
            if self.ai_manager:
                room_description: str = self.ai_manager.submit_request(
                    "Generate a description for a new room in my adventure game. Pre-existing room descriptions for inspiration:\n"
                    + "\n,\n".join(existing_room_descriptions[0:10])
                    + f"\nThis room is called '{room_name}'\n"
                    + "\nRespond with only a description of similar length to the ones above, nothing else.\n"
                )
                logger.info(f"AI-generated room description: {room_description}")
            else:
                return "Invalid input: room description missing and AI is not enabled."

        # Add the room
        error_message: str = self.world.add_room(
            player.get_current_location(),
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

    def make_purchase(self, item: GameItem, player: Player, merchant: Merchant) -> str:
        # Simply return True if the item is in the merchant's possession and the player said to buy
        if player.deduct_money(item.get_price()):
            transfer_issue = item.transfer(merchant, player)
            if transfer_issue:
                return transfer_issue
            # If no issue, tell the others about the transaction
            self.tell_others(
                player.sid,
                f"{player.name} has bought {item.get_name(article='the')} from {merchant.get_name()}.",
            )
            return f"Congratulations, you successfully purchased {item.get_name(article='the')} for {self.world.get_currency(item.get_price())}."

        return f"You do not have enough money to buy {item.get_name(article='the')}."

    def transact_buy_get(
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
                    return self.make_purchase(item, player, merchant)
        if found_count == 0:
            return f"There is no {item_name} to be found here."

    # Check if an item is in a merchant's possession
    def transact_item(self, item_name: str, player: Player, action: str = "get") -> str:
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
                return self.transact_buy_get(action, item_name, player, merchant)
        # If we get here, the item is not in any merchant's possession
        return f"You are unable to {action} '{item_name}' here."

    # Get / pick up an item
    def do_get(self, player: Player, rest_of_response: str) -> str:
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
                    self.tell_player(
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
                outcome: Optional[str] = self.transact_item(item_name, player, "get")
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

    def do_drop(self, player: Player, rest_of_response: str) -> str:
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
            self.tell_others(
                player.sid,
                f"{player.name} has dropped {drop_list_text}",
            )
            return "You drop " + drop_list_text
        else:
            if item_name == "all":
                return "You are not carrying anything."
            else:
                return f"You are not carrying '{item_name}'."

    def do_buy(self, player: Player, rest_of_response: str) -> str:
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
        return self.transact_item(item_name, player, "buy")

    def do_sell(self, player: Player, rest_of_response: str) -> str:
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
                self.tell_player(
                    player, self.transact_item(item.get_name(), player, "sell")
                )
        if item_name != "all" and found_count == 0:
            return f"You are not carrying '{item_name}'."

    def do_trade(self, player: Player, rest_of_response: str) -> str:
        # TODO #71 Implement trade command
        return "Support for this command coming soon!"

    def do_attack(self, player: Player, rest_of_response: str) -> str:
        return "This game does not condone violence! There must be another way to achieve your goal..."

    # Evaluate and if appropriate perform a custom action, which can modify the state of the location
    # And objects / entities in the vicinity
    def do_custom_action(self, player: Player, action: str) -> str:
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
        for other_entity in self.get_other_entities(player.sid):
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
            + "\n* The updated description of the current location in string property 'updated_location'."
            + "\n* The updated descriptions of any modified items (only those listed earlier) as nested object property 'updated_items', with item names as keys and new descriptions as values."
            + "\n* The descriptions of any newly created items as nested object property 'new_items', with new item names as keys and descriptions as values."
            + "\n* The descriptions of any destroyed/deleted items as string array 'deleted_items'."
            + " (If an item has changed so much that its name no longer applies, then delete it and replace it with one or more new items. Note that an item cannot be both updated and deleted.)"
            + "\n* The updated descriptions of any modified entities (only those listed earlier) as nested object property 'updated_entities', with entity names as keys and new descriptions as values."
            + "\nOnly include the updated elements if they have changed in a way that another player who did not witness the cause of the change would notice."
            + "\n If the command doesn't make sense or is too unrealistic, provide a meaningful response in JSON with element 'rejection_response'."
        )
        ai_response = self.ai_manager.submit_request(prompt)
        try:
            response_json = json.loads(ai_response)
        except json.JSONDecodeError:
            return "The AI could not understand the command."
        if response_json.get("success_response"):
            logger.info(
                f"AI understood the command and returned a success response: {response_json.get('success_response')}"
            )
            return_text: str = response_json.get("success_response")
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
            for item_name in response_json.get("deleted_items", []):
                self.world.delete_item(item_name, player)
            if response_json.get("new_items"):
                for item_name, new_description in response_json["new_items"].items():
                    # Create item
                    outcome = self.world.create_item(
                        item_name,
                        new_description,
                        player.get_current_location(),
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

        if " from " in rest_of_response:
            rest_of_response = rest_of_response.split(" from ")[0]

        # This is now simple because quotes are stripped out earlier
        return rest_of_response

    # Get a description of the players in the game
    def get_players_text(self) -> str:
        others_count: int = self.get_player_count() - 1
        if others_count == 0:
            return "You are the first player to join the game.\n"
        elif others_count == 1:
            return "You are the second player in the game.\n"
        else:
            return f"There are {others_count} other players in the game.\n"

    # Get location of player given a name
    def get_player_location_by_name(self, sid: str, player_name: str) -> Optional[str]:
        for other_entity in self.get_other_entities(sid):
            if str(other_entity.name).lower() == str(player_name).lower():
                return other_entity.get_current_location()
        return None

    # Get number of players in the game
    def get_player_count(self) -> int:
        return len(self.players)

    # Check if a player name is unique
    def is_existing_player_name(self, player_name: str) -> bool:
        for player_sid, player in self.players.items():
            if str(player.name).lower() == str(player_name).lower():
                return True
        return False

    # End of getters

    # Setters etc

    # Process player setup request from client
    def process_player_setup(
        self, sid: str, player_info: Dict[str, Any], help_message: str
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
            sid, player_name, player_info.get("role")
        )
        # Outcomes are adverse
        if outcome:
            return outcome

        # Register this player with the game server
        self.register_player(sid, player_info, player_name)

        # Tell other players about this new player
        self.tell_others(
            sid,
            f"{player_name} has joined the game, starting in the {player_info.get_current_location()}; there are now {self.get_player_count()} players.",
            shout=True,
        )

        # Tell this player about the game
        instructions: str = (
            f"Welcome to the game, {player_name}. "
            + self.list_players(sid)
            + " "
            + help_message
        )

        self.tell_player(player_info, instructions, type="instructions")

        self.tell_player(
            player_info,
            self.move_entity(player_info, "join", player_info.get_current_location()),
        )

        self.emit_game_data_update()

        # Spawn the world-wide metadata loop when the first player is created
        # This is to minimise resource usage when no one is playing.
        self.activate_background_loop()

    def list_players(self, sid: str) -> str:
        if self.get_player_count() == 1:
            return "You are the only player in the game currently."
        player_list = "Other players in the game: "
        for other_sid, player_name in self.player_sid_to_name_map.items():
            if other_sid != sid:
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
        logger.info(f"Checking for other entities than {player.sid}")
        for other_entity in self.get_other_entities(player.sid):
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

    def move_entity(
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
            for exit_dir, exit_room in self.world.rooms[entity.get_current_location()][
                "exits"
            ].items():
                if exit_room.lower() in direction.lower():
                    return self.move_entity(entity, exit_dir)

            return f"{direction} is not a valid direction or room name."

        # Check for other players you are leaving / joining
        for other_entity in self.get_other_entities(entity.sid, players_only=True):
            if other_entity.get_current_location() == entity.get_current_location():
                self.tell_player(
                    other_entity,
                    departure_message,
                )
            elif other_entity.get_current_location() == next_room:
                self.tell_player(
                    other_entity,
                    arrival_message,
                )

        message: str = ""
        if entity.is_player:
            message = self.build_move_outcome_message(
                entity, self.resolve_move_action(direction), next_room
            )
            # Emit update to player
            self.emit_player_room_update(entity, next_room)

        # Set new room
        entity.set_location(next_room)

        return message

    def register_player(self, sid: str, player: Player, player_name: str) -> Player:
        self.players[sid] = player
        self.player_sid_to_name_map[sid] = player_name
        return player

    # Emit a message about a room to a specific player
    def emit_player_room_update(self, player: Player, room: str) -> None:
        # Tell the player about the room including the image name
        self.sio.emit(
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
            player.sid,
        )

    # Emit a message to all players
    def tell_everyone(self, message: str) -> None:
        self.tell_others(None, message, shout=True)

    # Emit a message to all players except the one specified
    def tell_others(self, sid: Optional[str], message: str, shout: bool = False) -> int:
        told_count = 0
        if message.strip():
            for other_player_sid, other_player in self.players.items():
                # Only tell another player if they are in the same room
                if sid != other_player_sid and (
                    shout
                    or other_player.get_current_location()
                    == self.players[sid].get_current_location()
                ):
                    self.tell_player(other_player, message)
                    told_count += 1
        return told_count

    # Emit a message to a specific player
    def tell_player(
        self, player: Player, message: str, type: str = "game_update"
    ) -> None:
        message = message.strip()
        self.sio.emit(type, message, player.sid)
        player.add_input_history(f"Game: {message}")

    # Get other entities
    def get_other_entities(
        self, sid: Optional[str] = None, players_only: bool = False
    ) -> List[Union[Player, Entity]]:
        other_entities: List[Union[Player, Entity]] = []
        for other_player_sid, other_player in self.players.items():
            if sid is None or sid != other_player_sid:
                other_entities.append(other_player)
        if not players_only:
            for entity in self.world.entities.values():
                # Check if not player
                if not isinstance(entity, Player):
                    other_entities.append(entity)
        return other_entities

    # Emit game data update to all players
    def emit_game_data_update(self) -> None:
        if self.get_player_count() > 0:
            game_data: Dict[str, int] = {"player_count": self.get_player_count()}
            self.sio.emit(
                "game_data_update",
                game_data,
            )

    # Check each player to see if they have been inactive for too long
    def check_players_activity(self) -> None:
        current_time: float = time.time()
        sids_to_remove: List[str] = []
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
    def remove_player(self, sid: str, reason: str) -> None:
        if sid in self.players:
            player = self.players[sid]
            # Make player drop all items in their inventory
            self.tell_player(player, self.do_drop(player, "all"))
            # TODO #6 Create coin items corresponding to their money
            self.tell_player(
                player,
                reason,
            )
            message: str = (
                f"{player.name} has left the game; there are now {self.get_player_count()-1} players."
            )
            logger.info(message)
            self.tell_others(
                sid,
                message,
                shout=True,
            )
            self.emit_game_data_update()
            # Give player time to read the messages before logging them out
            eventlet.sleep(2)
            self.sio.emit("logout", reason, sid)
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
    def activate_background_loop(self) -> None:
        if not self.background_loop_active:
            logger.info("Activating background loop.")
            self.background_loop_active = True
            print("Spawning background loop")
            eventlet.spawn(self.game_background_loop)

    # Cause the game background loop to exit
    def deactivate_background_loop(self) -> None:
        logger.info("Deactivating background loop.")
        self.background_loop_active = False

    # This loop runs in the background to do things like broadcast player count
    # It only runs when there are players in the game
    def game_background_loop(self) -> None:
        while self.background_loop_active:
            # Run the loop periodically
            eventlet.sleep(self.game_loop_time_secs)

            # Time out players who do nothing for too long.
            self.check_players_activity()

            # Broadcast player count
            # So that AI players can pause when there are no human players, saving money
            self.emit_game_data_update()

            # Move animals around
            direction: str
            for animal in self.get_entities("animal"):
                direction = animal.maybe_pick_direction_to_move()
                if direction:
                    logger.info(f"Moving {animal.name} {direction}")
                    self.move_entity(animal, direction)
                else:
                    gesture_description: str = animal.maybe_gesture()
                    if gesture_description:
                        logger.info(f"{animal.name} will gesture {gesture_description}")
                        # Check for other players who will witness the gesture
                        for other_entity in self.get_other_entities(
                            None, players_only=True
                        ):
                            if (
                                other_entity.get_current_location()
                                == animal.get_current_location()
                            ):
                                self.tell_player(
                                    other_entity,
                                    gesture_description,
                                )
