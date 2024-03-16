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
        move_chance=0,  # 0 to 1
    ):
        # Note that there can be many instances of the same named animal

        logger.info(f"Creating animal of type {animal_name}")

        # Set up entity.
        Entity.__init__(self, world, animal_name, "animal", starting_room, description)

        self.move_chance = move_chance
        self.gestures = gestures or []

    # Future animal-specific behaviours and attributes coming soon!
    def make_gesture(self):
        gesture = random.choice(self.gestures)
        return f"The {self.name} {gesture}"

    def move_around(self):
        if random.random() < self.move_chance:
            self.move_to_room(
                random.choice(self.world.get_room_exits(self.current_room))
            )

    def get_name(self):
        return "A " + self.name
