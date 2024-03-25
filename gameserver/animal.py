from logger import setup_logger, debug

# Set up logger
logger = setup_logger()

from entity import Entity
import random


# Animal class
class Animal(Entity):
    def __init__(
        self,
        world,
        name,
        location,
        description="",
        actions=None,
        action_chance=0,  # 0 to 1
    ):
        # Note that there can be many instances of the same named animal

        logger.info(f"Creating animal of type {name}")

        # Set up entity.
        Entity.__init__(self, world, name, "animal", location, description)

        self.action_chance = action_chance
        self.actions = actions or []

    # Future animal-specific behaviours and attributes coming soon!
    def maybe_gesture(self):
        r = random.random()
        debug(r, self.action_chance)
        if r < self.action_chance:
            gesture = random.choice(self.actions)
            return f"The {self.name} {gesture}."

    def maybe_pick_direction_to_move(self):
        r = random.random()
        debug(r, self.action_chance)
        if r < self.action_chance:
            possible_exits = list(self.world.rooms[self.location]["exits"].keys())
            direction = random.choice(possible_exits)
            return direction
        return ""
