import os
import time
from logger import setup_logger
from character import Character

# Set up logging
logger = setup_logger()


# Player class
class Player(Character):
    def __init__(self, world, sid, player_name, player_role):
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

        # Set up character
        print("DEBUG: Setting up character")
        # TODO: Remove this, it's for simulating AI builders
        if player_name == "Doug":
            player_role = "builder"
        else:
            player_role = player_role or "player"
        print(world, player_name, player_role)
        #Call superclass constructor
        Character.__init__(
            self, world, player_name, player_role
        )

        # Set flag to indicate this is a player
        self.is_player = True

        # Set default score
        self.money = (
            100  # TODO: change this to 0 once other ways to earn money are implemented
        )

        # Last action time is used to check for idle players
        self.last_action_time = time.time()

        # Register of rooms this player has visited before (so they don't get long descriptions again)
        self.seen_rooms = {}
        self.seen_rooms[self.current_room] = True

        # SID is the unique identifier for this player used by SocketIO
        self.sid = sid

    # Setter for updating player's last action time
    # Used to check for idle players
    def update_last_action_time(self):
        self.last_action_time = time.time()

    # Get inventory description
    def get_inventory_description(self):
        description = "You are carrying: "
        for object in self.get_inventory():
            description += object.get_name("a") + ", "
        #Add money to inventory description
        description =  description[:-2] + f".\nYou also have {self.world.get_currency(self.money)} in your pocket."
        return description

    def deduct_money(self, amount):
        if self.money < amount:
            return False
        else:
            self.money -= amount
            return True

    def add_money(self, amount):
        self.money += amount
