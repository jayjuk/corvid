from typing import Optional, Dict, Any
from logger import setup_logger, exit

# Set up logger
logger = setup_logger()


# Player class
class GameItem:
    def __init__(
        self,
        world: "World",
        name: Optional[str] = None,
        description: Optional[str] = None,
        price: int = 0,
        location: Optional[str] = None,
        init_dict: Optional[Dict[str, Any]] = None,
    ) -> None:
        if init_dict:
            self.__dict__.update(init_dict)
        elif name:
            self.name: str = name
            self.description: Optional[str] = description
            self.location: Optional[str] = location
            self.price: int = price

        # An item belongs to a world
        self.world: "World" = world

        self.check_item_name(self.name)
        if (
            hasattr(self, "location")
            and self.location not in world.rooms
            and self.location not in world.get_entity_names()
        ):
            # This can be caused by the game server being killed while a player is holding an item.
            # In this case, the item location will be a player's name, which is not a valid location if that player is not playing.
            logger.warning(
                f"Invalid location {self.location} specified for item {self.name}"
            )
            # First try to use starting location
            if hasattr(self, "starting_location"):
                self.set_location(self.starting_location)
            else:
                # Set default location
                self.set_location(world.get_default_location())

        # Check item has starting location, if not, set to current location
        # This is used to track where the item was originally created
        if not (hasattr(self, "starting_location")):
            self.set_starting_location(self.location)

        logger.debug(f"Creating item {self.name}" + f" starting in {self.location}")

    def check_item_name(self, item_name: str) -> None:
        if not item_name:
            exit(logger, "Item must have a name")
        for reserved_word in (" from ", " up ", " to "):
            if reserved_word in item_name.lower():
                exit(
                    logger,
                    f"Problems will arise if an item is created that contains '{reserved_word}'.",
                )

    # Getter for player's current location
    def get_location(self) -> Optional[str]:
        return self.location

    def set_location(self, location: str) -> None:
        self.location = location
        self.world.storage_manager.store_game_object(self.world.name, self)

    def set_starting_location(self, location: str) -> None:
        self.starting_location = location
        self.world.storage_manager.store_game_object(self.world.name, self)

    # Setter (i.e. player drops it)
    def set_room(self, room_name: str) -> None:
        if room_name is None:
            exit(logger, f"{self.name} is being dropped in a non-existent room")
        logger.info(f"{self.name} is being dropped in {room_name}")
        self.set_location(room_name)
        self.world.add_item_to_room(self, room_name)

    # Setter for player picking up
    def set_possession(self, entity: "Entity") -> str:
        # Remove from room in which receiving entity is
        self.world.remove_item_from_room(self, entity.location)
        self.set_location(entity.name)
        # Try to add the item to the player's inventory, if it fails, return an error string, no error means success
        add_item_error: str = entity.add_item(self)
        if add_item_error:
            return add_item_error

        # Return empty string means it's been picked up without issue
        return ""

    # Remove from old player and add to new player
    def transfer(self, old_entity: "Entity", new_entity: "Entity") -> str:
        if new_entity.can_add_item():
            if old_entity.drop_item(self):
                outcome: str = self.set_possession(new_entity)
                if outcome:
                    # If there was an error, return it
                    return outcome
                if not outcome:
                    # Remove from room
                    # TODO #73 Review and improve item transfer going up from item to world
                    return self.world.remove_item_from_room(
                        self, new_entity.get_current_location()
                    )

            else:
                return f"{old_entity.get_name()} can't drop {self.name}."
        else:
            return f"{new_entity.get_name()} can't carry any more."

    # Description of the item
    def get_description(self) -> Optional[str]:
        return self.description

    # Description of the item
    def get_price(self) -> int:
        return self.price

    # Name of the item
    def get_name(self, article: str = "") -> str:
        # Adjust article (if any) for the name of the item
        if article == "a" and self.name[0].lower() in "aeiou":
            article = "an "
        elif article != "":
            article += " "
        return f"{article}{self.name}"
