from typing import List, Optional
from utils import setup_logger
from gameitem import GameItem

# Set up logger
logger = setup_logger()


class Entity:

    def __init__(
        self,
        world: "World",
        entity_name: str,
        entity_role: str,
        location: Optional[str] = None,
        description: Optional[str] = None,
    ):
        self.name: str = entity_name
        self.role: str = entity_role
        self.is_player: bool = False
        self.sid: Optional[str] = None  # Overridden for players
        self.description: Optional[str] = description

        # Default starting location
        self.location: str = location or world.get_location()

        # Inventory
        self.inventory: List[GameItem] = []

        # Register this entity in the world it belongs in
        world.register_entity(self)

        # Save reference to the world this entity is in
        self.world: "World" = world

    # Setter for player's location change
    def set_location(self, next_room: str) -> None:
        # Set new room
        self.location = next_room
        # Store change of location
        self.world.storage_manager.store_game_object(self.world.name, self)

    # Getter for player's current location
    def get_current_location(self) -> str:
        return self.location

    def can_add_item(self) -> bool:
        # Default behaviour for entities is to not allow them to pick up items
        return False

    # Setter for player picking up an item
    def add_item(self, item: GameItem) -> None:
        self.inventory.append(item)

    # Setter for player dropping item by reference
    def drop_item(
        self, item: GameItem, dropped_items: Optional[List[GameItem]] = None
    ) -> List[GameItem]:
        if dropped_items is None:
            dropped_items = []
        self.inventory.remove(item)
        item.set_room(self.location)
        dropped_items.append(item)
        return dropped_items

    # Setter for player dropping item by name
    def drop_items(self, item_name: str) -> List[GameItem]:
        # Check if item is a string
        dropped_items = []
        if isinstance(item_name, str):
            # Check if item is in inventory
            for item in self.inventory.copy():
                if (
                    item_name.lower() in item.get_name().lower()
                    or item_name.lower() == "all"
                ):
                    self.drop_item(item, dropped_items)
        return dropped_items

    def get_inventory(self) -> List[GameItem]:
        return self.inventory

    def get_inventory_description(self) -> str:
        # Superclass / default implementation is blank as only certain entities will have an inventory
        return ""

    def get_is_player(self) -> bool:
        return self.is_player

    def get_name(self, article_type: Optional[str] = None) -> str:
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

    def get_description(self) -> str:
        if self.description:
            return self.description
        return f"You see nothing special about {self.get_name()}."

    def get_role(self) -> str:
        return self.role
