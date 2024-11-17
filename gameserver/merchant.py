from typing import List, Optional
from utils import setup_logger
from entity import Entity
from gameitem import GameItem

# Set up logger
logger = setup_logger()


# Merchant class
class Merchant(Entity):
    def __init__(
        self,
        world: "World",
        name: str,
        location: str,
        inventory: Optional[List[GameItem]] = None,
        description: str = "",
    ):
        # First check
        logger.debug(f"Creating merchant {name}")

        # Set up entity
        super().__init__(world, name, "merchant", location, description)

        if inventory is None:
            inventory = []
        for item in inventory:
            # Add item to merchant's inventory
            item.set_possession(self)

    # Get inventory description
    def get_inventory_description(self) -> str:
        description: str = ""
        for item in self.get_inventory():
            description += f"{item.get_name('a')} ({self.world.get_currency(item.get_price(), short=True)}), "
        if description:
            return (
                "They have the following available for sale: " + description[:-2] + "."
            )
        return "They do not currently have anything to sell."

    # Overridden method to get description of merchant including their inventory.
    def get_description(self) -> str:
        return self.description + " " + self.get_inventory_description()

    # Overridden method to allow them to receive items
    def can_add_item(self) -> bool:
        return True
