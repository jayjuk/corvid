from logger import setup_logger

# Set up logger
logger = setup_logger()

from entity import Entity


# Merchant class
class Merchant(Entity):
    def __init__(self, world, name, location, inventory=[], description=""):
        # First check
        logger.info(f"Creating merchant {name}")

        # Set up entity
        Entity.__init__(self, world, name, "merchant", location, description)

        for object in inventory:
            # Add object to merchant's inventory
            object.set_possession(self)

    # Get inventory description
    def get_inventory_description(self):
        description = ""
        for object in self.get_inventory():
            description += f"{object.get_name('a')} ({self.world.get_currency(object.get_price(), short=True)}), "
        if description:
            return (
                "They have the following available for sale: " + description[:-2] + "."
            )
        return "They do not currently have anything to sell."

    # Overridden method to get description of merchant including their inventory.
    def get_description(self):
        return self.description + " " + self.get_inventory_description()

    # Overridden method to allow them to receive objects
    def can_add_object(self):
        return True
