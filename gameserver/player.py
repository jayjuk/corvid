from typing import Optional, Dict, List, Any
from utils import setup_logger, exit
import os
import time
from entity import Entity
from typing import List, Optional
from gameitem import GameItem

# Set up logger
logger = setup_logger()


# Player class
class Player(Entity):
    def __init__(
        self,
        world: Any,
        sid: str,
        player_name: str,
        player_role: str = "player",
        stored_player_data: Optional[Dict[str, Any]] = None,
    ) -> None:
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
                f"Sorry, name {player_name} is not valid, it should be up to 20 alphabetical characters only. Please try again."
            )

        # Set up player
        # TODO #74 Remove this, it's for simulating AI builders
        if player_name in ("Doug", "Alice", "Bob"):
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
            self.seen_rooms: Dict[str, bool] = {}
            self.seen_rooms[self.location] = True

            # SID is the unique identifier for this player used by SocketIO
            self.sid = sid

        # Define history - this resets each time the player logs in
        self.max_input_history_length = 1000
        self.input_history: List[str] = []

        # Define inventory limit for players
        self.max_inventory = 5

        self.last_login = time.time()

        # Last action time is used to check for idle players, always refresh this
        self.last_action_time = time.time()

    def get_input_history(self, number_of_entries: int = 1, prefix: str = "") -> str:
        """Return some input history (optional input of number of entries to return)."""
        output: str = prefix + ("\n" if prefix else "")
        # Resolve start index of array: do not show the first entry which will be the instructions
        if len(self.input_history) < 2:
            return ""
        number_of_entries = min(number_of_entries, len(self.input_history) - 1)
        output += "\n".join(self.input_history[-number_of_entries:]) + "\n"
        return output

    # Setter for input history - add a new entry but don't let it get above a certain length
    def add_input_history(self, input: str) -> None:
        self.input_history.append(input)
        if len(self.input_history) > self.max_input_history_length:
            self.input_history.pop(0)

    # Setter for updating player's last action time
    # Used to check for idle players
    def update_last_action_time(self) -> None:
        self.last_action_time = time.time()

    # Get inventory description
    def get_inventory_description(self) -> str:
        description: str
        if not self.get_inventory():
            description = "You are not carrying any items. You "
        else:
            description = "You are carrying: "
            for item in self.get_inventory():
                description += item.get_name("a") + ", "
            # Add money to inventory description
            description = description[:-2] + ".\nYou also "
        description += f"have {self.world.get_currency(self.money)} in your pocket."
        return description

    def deduct_money(self, amount: int) -> bool:
        if self.money < amount:
            return False
        else:
            self.money -= amount
            # Store change
            self.world.storage_manager.store_game_object(self.world.name, self)
            return True

    def add_money(self, amount: int) -> None:
        self.money += amount
        # Store change
        self.world.storage_manager.store_game_object(self.world.name, self)

    def can_add_item(self) -> bool:
        return len(self.inventory) < self.max_inventory

    # Override for player picking up an item - has a limit
    def add_item(self, item: GameItem) -> Optional[str]:
        if not self.can_add_item():
            return "You can't carry any more items."
        self.inventory.append(item)

    # Override for player's location change
    def set_location(self, next_room: str) -> None:
        # Superclass behaviour
        super().set_location(next_room)
        # Also flag this room as seen
        self.seen_rooms[self.location] = True
