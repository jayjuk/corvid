from logger import setup_logger

# Set up logger
logger = setup_logger()

import os
import time
from entity import Entity


# Player class
class Player(Entity):
    def __init__(
        self, world, sid, player_name, player_role="player", stored_player_data=None
    ):
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

        # Set up player
        # TODO #74 Remove this, it's for simulating AI builders
        if player_name == "Doug":
            player_role = "builder"

        # Call superclass constructor
        Entity.__init__(self, world, player_name, player_role)

        if stored_player_data:
            logger.info(f"Retrieved player {player_name} data from database")
            self.__dict__.update(stored_player_data)
            # But use latest sid and make world object
            self.sid = sid
            self.world = world
        else:
            logger.info(f"Creating player {player_name}, sid {sid}")

            # Set flag to indicate this is a player
            self.is_player = True

            # Set default score
            # TODO #75 Change starting money to 0 once other ways to earn money are implemented
            self.money = 100

            # Register of rooms this player has visited before (so they don't get long descriptions again)
            self.seen_rooms = {}
            self.seen_rooms[self.location] = True

            # SID is the unique identifier for this player used by SocketIO
            self.sid = sid

            # Define history
            self.max_input_history_length = 1000
            self.input_history = []

            # Define inventory limit for players
            self.max_inventory = 5

        self.last_login = time.time()

        # Last action time is used to check for idle players, always refresh this
        self.last_action_time = time.time()

    # Getter for input history (optional input of number of entries to return)
    def get_input_history(self, number_of_entries=1):
        return "\n".join(self.input_history[-number_of_entries:]) + "\n"

    # Setter for input history - add a new entry but don't let it get above a certain length
    def add_input_history(self, input):
        self.input_history.append(input)
        if len(self.input_history) > self.max_input_history_length:
            self.input_history.pop(0)

    # Setter for updating player's last action time
    # Used to check for idle players
    def update_last_action_time(self):
        self.last_action_time = time.time()

    # Get inventory description
    def get_inventory_description(self):
        if not self.get_inventory():
            description = "You are not carrying any objects. You "
        else:
            description = "You are carrying: "
            for object in self.get_inventory():
                description += object.get_name("a") + ", "
            # Add money to inventory description
            description = description[:-2] + ".\nYou also "
        description += f"have {self.world.get_currency(self.money)} in your pocket."
        return description

    def deduct_money(self, amount):
        if self.money < amount:
            return False
        else:
            self.money -= amount
            # Store change
            self.world.storage_manager.store_game_object(self.world.name, self)
            return True

    def add_money(self, amount):
        self.money += amount
        # Store change
        self.world.storage_manager.store_game_object(self.world.name, self)

    def can_add_object(self):
        return len(self.inventory) < self.max_inventory

    # Override for player picking up an object - has a limit
    def add_object(self, object):
        if not self.can_add_object():
            return "You can't carry any more items."
        self.inventory.append(object)

    # Override for player's location change
    def set_location(self, next_room):
        # Superclass behaviour
        super().set_location(next_room)
        # Also flag this room as seen
        self.seen_rooms[self.location] = True
