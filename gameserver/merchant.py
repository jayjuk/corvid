from logger import setup_logger

# Set up logger
logger = setup_logger()

from character import Character


# Player class
class Merchant(Character):
    def __init__(
        self, world, merchant_name, starting_room, inventory=[], description=""
    ):
        # First check
        logger.info(f"Creating merchant {merchant_name}")

        # Set up character
        Character.__init__(
            self, world, merchant_name, "merchant", starting_room, description
        )

        # Register NPC in the world
        # TODO: consider creating a class NPC between Character and Merchant
        world.register_npc(self)

        for object in inventory:
            # Add object to merchant's inventory
            object.set_possession(self)

    # Get inventory description
    def get_inventory_description(self):
        description = "They have the following available for sale: "
        for object in self.get_inventory():
            description += f"{object.get_name('a')} ({self.world.get_currency(object.get_price(), short=True)}), "
        return description[:-2] + "."

    # Overridden method to get description of merchant including their inventory.
    def get_description(self):
        return self.description + " " + self.get_inventory_description()

    # Overridden method to allow them to receive objects
    def can_add_object(self):
        return True
