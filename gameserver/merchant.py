from logger import setup_logger
from character import Character

# Set up logging
logger = setup_logger()


# Player class
class Merchant(Character):
    def __init__(self, world, merchant_name, starting_room, inventory=None):
        # First check
        logger.info(f"Creating merchant {merchant_name}")

        # Set up character
        Character.__init__(self, world, merchant_name, "merchant", starting_room)

        if inventory:
            self.inventory = inventory

    # Get inventory description
    def get_inventory_description(self):
        description = "The merchant has the following available for sale: "
        for object in self.get_inventory():
            description += f"{object.get_name('a')} ({'' if object.get_price()==0 else str(object.get_price())}), "
        return description[:-2] + "."
