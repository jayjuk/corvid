from typing import List, Optional
from utils import set_up_logger
from entity import Entity
import random

# Set up logger
logger = set_up_logger()


# Animal class
class Animal(Entity):
    def __init__(
        self,
        world: "World",
        name: str,
        location: str,
        description: str = "",
        actions: Optional[List[str]] = None,
        action_chance: float = 0,  # 0 to 1
        move_chance: float = 0,  # 0 to 1
    ):
        # Note that there can be many instances of the same named animal

        logger.debug(f"Creating animal of type {name}")

        # Set up entity.
        Entity.__init__(self, world, name, "animal", location, description)

        self.action_chance = action_chance
        self.move_chance = move_chance or self.action_chance
        self.actions = actions or []

    # Future animal-specific behaviours and attributes coming soon!
    def maybe_gesture(self) -> str:
        r = random.random()
        if r < self.action_chance:
            gesture = random.choice(self.actions)
            return f"The {self.name} {gesture}."
        return ""

    def maybe_pick_direction_to_move(self) -> str:
        r = random.random()
        if r < self.move_chance:
            possible_exits = self.world.get_exits(self.location)
            if possible_exits:
                return random.choice(possible_exits)
        return ""
