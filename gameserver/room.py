from logger import setup_logger, exit

# Set up logger
logger = setup_logger()


# Player class
class Room:

    def __init__(
        self,
        world,
        name=None,
        description=None,
        exits=None,
        init_dict=None,
        creator=None,
        image=None,
        grid_reference=None,
    ):
        if init_dict:
            self.__dict__.update(init_dict)
            # Override world (in DB it is the game name, we need a pointer to the world object)
        else:
            self.name = name
            self.description = description
            self.exits = exits
            self.creator = creator
            self.image = image
            self.grid_reference = grid_reference

        # An object belongs to a world
        self.world = world

        logger.info(f"Creating room {self.name}")
