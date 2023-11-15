import os
import time
from logger import setup_logger

# Set up logging
logger = setup_logger()


# Player class
class Player:
    # Game manager reference applies to all players
    game_manager = None

    def __init__(self, game_manager, sid, player_name, player_role, starting_room):
        # First check if player name is valid
        if not (
            player_name
            and len(player_name) <= 20
            and player_name.isprintable()
            and player_name.isalpha()
            and os.path.normpath(player_name).replace(os.sep, "_") == player_name
        ):
            # Issue with player name setting
            raise ValueError(
                "Sorry, that name is not valid, it should be up to 20 alphabetical characters only. Please try again."
            )

        logger.info(f"Creating player {player_name}, sid {sid}")

        # Register game server reference in player object to help with testing and minimise use of globals
        if Player.game_manager is None and game_manager is not None:
            Player.game_manager = game_manager
        self.last_action_time = time.time()
        self.player_name = player_name

        # TODO: Remove this, it's for simulating AI builders
        if player_name == "Doug":
            self.role = "builder"
        else:
            self.role = player_role

        # Default starting location
        self.current_room = starting_room

        # Register of rooms this player has visited before (so they don't get long descriptions again)
        self.seen_rooms = {}
        self.seen_rooms[self.current_room] = True

        # SID is the unique identifier for this player used by SocketIO
        self.sid = sid

        # Inventory
        self.inventory = []

    # Setter for updating player's last action time
    # Used to check for idle players
    def update_last_action_time(self):
        self.last_action_time = time.time()

    # Setter for player's location change
    def move_to_room(self, next_room):
        # Set new room
        self.current_room = next_room
        # Flag this room as seen
        self.seen_rooms[self.current_room] = True

    # Getter for player's current location
    def get_current_room(self):
        return self.current_room

    # Setter for player picking up an object
    def add_object(self, object):
        self.inventory.append(object)

    # Setter for player dropping an object
    def drop_object(self, object_name):
        for object in self.inventory:
            if object.get_name().lower() == object_name.lower():
                self.inventory.remove(object)
                object.set_room(self.current_room)
                return object

    def get_inventory(self):
        return self.inventory

    def get_inventory_description(self):
        description = "You are carrying: "
        for object in self.get_inventory():
            description += object.get_name("a") + ", "
        return description[:-2] + "."
