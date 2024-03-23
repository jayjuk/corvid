from logger import setup_logger, exit

# Set up logger
logger = setup_logger()


# Player class
class Object:
    def __init__(
        self,
        world_ref,
        object_name=None,
        object_description=None,
        price=0,
        location=None,
        init_dict=None,
    ):
        if init_dict:
            self.__dict__.update(init_dict)
            # Override world (in DB it is the game name, we need a pointer to the world object)
            self.world = world_ref
            # TODO: remove this once migration from old objects is complete
            # if hasattr(self, "starting_room"):
            #    self.location = self.starting_room
            #    del self.starting_room
        else:
            if object_name:
                self.name = object_name
                self.description = object_description
                self.location = location
                self.price = price

        # An object belongs to a world
        self.world = world_ref

        self.check_object_name(self.name)
        # if (
        #     hasattr(self, "location")
        #     and world_ref
        #     and self.location is not None
        #     and self.location != "None"
        #     and self.location not in world_ref.rooms
        #     and self.location not in world_ref.get_entity_names()
        # ):
        #     exit(
        #         logger,
        #         f"Invalid location {location} specified for object {self.name}",
        #     )

        logger.info(f"Creating object {self.name}" + f" starting in {self.location}")

    def check_object_name(self, object_name):
        if not object_name:
            exit(logger, "Object must have a name")
        for reserved_word in (" from ", " up ", " to "):
            if reserved_word in object_name.lower():
                exit(
                    logger,
                    "Problems will arise if an object is created that contains '{}'.",
                )

    # Getter for player's current location
    def get_location(self):
        return self.location

    def set_location(self, location):
        self.location = location
        # TODO: Is this a bit gross? if so, where should this live?
        self.world.storage_manager.store_python_object(self.world.name, self)

    # Setter (i.e. player drops it)
    def set_room(self, room_name):
        if room_name is None:
            exit(logger, f"{self.name} is being dropped in a non-existent room")
        logger.info(f"{self.name} is being dropped in {room_name}")
        self.set_location(room_name)
        self.world.add_object_to_room(self, room_name)

    # Setter for player picking up
    def set_possession(self, entity):
        # Remove from room in which receiving entity is
        self.world.remove_object_from_room(self, entity.location)
        self.set_location(entity.name)
        # Try to add the object to the player's inventory, if it fails, return an error string, no error means success
        add_object_error = entity.add_object(self)
        if add_object_error:
            return add_object_error

        # Return empty string means it's been picked up without issue
        return ""

    # Remove from old player and add to new player
    def transfer(self, old_entity, new_entity):
        if new_entity.can_add_object():
            if old_entity.drop_object(self):
                outcome = self.set_possession(new_entity)
                if not outcome:
                    # Remove from room
                    # TODO: review if this is right way to do it
                    self.world.remove_object_from_room(
                        self, new_entity.get_current_room()
                    )

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
