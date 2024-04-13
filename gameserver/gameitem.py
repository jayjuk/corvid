from logger import setup_logger, exit

# Set up logger
logger = setup_logger()


# Player class
class GameItem:
    def __init__(
        self,
        world,
        name=None,
        description=None,
        price=0,
        location=None,
        init_dict=None,
    ):
        if init_dict:
            self.__dict__.update(init_dict)
        elif name:
            self.name = name
            self.description = description
            self.location = location
            self.price = price

        # An item belongs to a world
        self.world = world

        self.check_item_name(self.name)
        if (
            hasattr(self, "location")
            and self.location not in world.rooms
            and self.location not in world.get_entity_names()
        ):
            exit(
                logger,
                f"Invalid location {location} specified for item {self.name}",
            )

        logger.info(f"Creating item {self.name}" + f" starting in {self.location}")

    def check_item_name(self, item_name):
        if not item_name:
            exit(logger, "Item must have a name")
        for reserved_word in (" from ", " up ", " to "):
            if reserved_word in item_name.lower():
                exit(
                    logger,
                    "Problems will arise if an item is created that contains '{}'.",
                )

    # Getter for player's current location
    def get_location(self):
        return self.location

    def set_location(self, location):
        self.location = location
        self.world.storage_manager.store_game_object(self.world.name, self)

    # Setter (i.e. player drops it)
    def set_room(self, room_name):
        if room_name is None:
            exit(logger, f"{self.name} is being dropped in a non-existent room")
        logger.info(f"{self.name} is being dropped in {room_name}")
        self.set_location(room_name)
        self.world.add_item_to_room(self, room_name)

    # Setter for player picking up
    def set_possession(self, entity):
        # Remove from room in which receiving entity is
        self.world.remove_item_from_room(self, entity.location)
        self.set_location(entity.name)
        # Try to add the item to the player's inventory, if it fails, return an error string, no error means success
        add_item_error = entity.add_item(self)
        if add_item_error:
            return add_item_error

        # Return empty string means it's been picked up without issue
        return ""

    # Remove from old player and add to new player
    def transfer(self, old_entity, new_entity):
        if new_entity.can_add_item():
            if old_entity.drop_item(self):
                outcome = self.set_possession(new_entity)
                if not outcome:
                    # Remove from room
                    # TODO #73 Review and improve item transfer going up from item to world
                    self.world.remove_item_from_room(
                        self, new_entity.get_current_location()
                    )

            else:
                return f"{old_entity.get_name()} can't drop {self.name}."
        return f"{new_entity.get_name()} can't carry any more."

    # Description of the item
    def get_description(self):
        return self.description

    # Description of the item
    def get_price(self):
        return self.price

    # Name of the item
    def get_name(self, article=""):
        # Adjust article (if any) for the name of the item
        if article == "a" and self.name[0].lower() in "aeiou":
            article = "an "
        elif article != "":
            article += " "
        return f"{article}{self.name}"
