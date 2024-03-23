from logger import setup_logger

# Set up logger
logger = setup_logger()


class Entity:
    # World reference applies to all entities
    world = None

    def __init__(
        self,
        world,
        entity_name,
        entity_role,
        location=None,
        description=None,
    ):
        # Register game server reference in player object to help with testing and minimise use of globals
        if self.__class__.world is None and world is not None:
            self.__class__.world = world

        self.name = entity_name
        self.role = entity_role
        self.is_player = False
        self.sid = None  # Overridden for players
        self.description = description

        # Default starting location
        self.location = location or world.get_location()

        # Inventory
        self.inventory = []

        # Register this entity in the world it belongs in
        world.register_entity(self)

    # Setter for player's location change
    def move_to_room(self, next_room):
        # Set new room
        self.location = next_room

    # Getter for player's current location
    def get_current_room(self):
        return self.location

    def can_add_object(self):
        # Default behaviour for entities is to not allow them to pick up objects
        return False

    # Setter for player picking up an object
    def add_object(self, object):
        self.inventory.append(object)

    # Setter for player dropping object by reference
    def drop_object(self, object, dropped_objects=None):
        if dropped_objects is None:
            dropped_objects = []
        self.inventory.remove(object)
        object.set_room(self.location)
        dropped_objects.append(object)
        return dropped_objects

    # Setter for player dropping objects by name
    def drop_objects(self, object_name):
        # Check if object is a string
        dropped_objects = []
        if isinstance(object_name, str):
            # Check if object is in inventory
            for object in self.inventory.copy():
                logger.debug("you have " + object.get_name().lower())
                if (
                    object_name.lower() in object.get_name().lower()
                    or object_name.lower() == "all"
                ):
                    self.drop_object(object, dropped_objects)
        return dropped_objects

    def get_inventory(self):
        return self.inventory

    def get_inventory_description(self):
        # Superclass / default implementation is blank as only certain entities will have an inventory
        return ""

    def get_is_player(self):
        return self.is_player

    def get_name(self, article_type=None):
        if article_type == "definite":
            if self.get_role() == "animal":
                return f"The {self.name}"
            if self.get_role() == "merchant":
                return "The merchant"
        if article_type == "indefinite":
            if self.get_role() == "animal":
                return f"a {self.name}"
            if self.get_role() == "merchant":
                return "a merchant"
            return "a player"
        if self.get_role() == "animal":
            return f"a {self.name}"
        return (
            f"{self.name}{' The ' + str(self.role).capitalize() if self.role else ''}"
        )

    def get_description(self):
        if self.description:
            return self.description
        return f"You see nothing special about {self.get_name()}."

    def get_role(self):
        return self.role
