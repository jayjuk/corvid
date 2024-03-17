from logger import setup_logger

# Set up logger
logger = setup_logger()

from entity import Entity
import random


# Animal class
class Animal(Entity):
    def __init__(
        self,
        world,
        animal_name,
        starting_room,
        description="",
        gestures=None,
        action_chance=0,  # 0 to 1
    ):
        # Note that there can be many instances of the same named animal

        logger.info(f"Creating animal of type {animal_name}")

        # Set up entity.
        Entity.__init__(self, world, animal_name, "animal", starting_room, description)

        self.action_chance = action_chance
        self.gestures = gestures or []

    # Future animal-specific behaviours and attributes coming soon!
    def maybe_gesture(self):
        if random.random() < self.action_chance:
            gesture = random.choice(self.gestures)
            return f"The {self.name} {gesture}."

    def maybe_pick_direction_to_move(self):
        if random.random() < self.action_chance:
            possible_exits = list(self.world.rooms[self.current_room]["exits"].keys())
            direction = random.choice(possible_exits)
            return direction
        return ""
