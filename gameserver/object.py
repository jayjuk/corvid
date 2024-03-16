from logger import setup_logger

# Set up logger
logger = setup_logger()


# Player class
class Object:
    def __init__(
        self, world_ref, object_name, object_description, price=0, starting_room=None
    ):
        logger.info(
            f"Creating object {object_name}" + f" starting in {starting_room}"
            if starting_room is not None
            else ""
        )

        # An object belongs to a world and has a name, a description and a location
        self.world = world_ref
        self.name = object_name
        self.description = object_description
        self.room = starting_room
        # An object can be in the player's possession but doesn't start that way
        self.player_possession = None
        self.price = price

    # Getter for player's current location
    def get_room(self):
        return self.room

    # Setter (i.e. player drops it)
    def set_room(self, room_name):
        if room_name is None:
            logger.error(f"{self.name} is being dropped in a non-existent room")
            exit()
        logger.info(f"{self.name} is being dropped in {room_name}")
        self.room = room_name
        self.player_possession = None
        self.world.add_object_to_room(self, room_name)

    # Setter for player picking up
    def set_possession(self, entity):
        self.room = None
        # Set the player possession to the player both ways
        self.player_possession = entity
        # Try to add the object to the player's inventory, if it fails, return an error string, no error means success
        add_object_error = entity.add_object(self)
        if add_object_error:
            return add_object_error

        # Remove from room
        self.world.remove_object_from_room(self, entity.get_current_room())
        # Return empty string means it's been picked up without issue
        return ""

    # Remove from old player and add to new player
    def transfer(self, old_entity, new_entity):
        if new_entity.can_add_object():
            if old_entity.drop_object(self):
                return self.set_possession(new_entity)
            else:
                return f"{old_entity.get_name()} can't drop {self.name}."
        return f"{new_entity.get_name()} can't carry any more."

    # Description of the object
    def get_description(self):
        return self.description

    # Description of the object
    def get_price(self):
        return self.price

    # Name of the object
    def get_name(self, article=""):
        # Adjust article (if any) for the name of the object
        if article == "a" and self.name[0].lower() in "aeiou":
            article = "an "
        elif article != "":
            article += " "
        return f"{article}{self.name}"
