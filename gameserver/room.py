from typing import Dict, Optional, Any
from logger import setup_logger, exit

# Set up logger
logger = setup_logger()


# Player class
class Room:

    def __init__(
        self,
        world: "World",
        name: Optional[str] = None,
        description: Optional[str] = None,
        exits: Optional[Dict[str, str]] = None,
        init_dict: Optional[Dict[str, Any]] = None,
        creator: Optional[str] = None,
        image: Optional[bytes] = None,
        grid_reference: Optional[str] = None,
    ) -> None:
        if init_dict:
            self.__dict__.update(init_dict)
            # Override world (in DB it is the game name, we need a pointer to the world object)
        else:
            self.name: Optional[str] = name
            self.description: Optional[str] = description
            self.exits: Optional[Dict[str, str]] = exits
            self.creator: Optional[str] = creator
            self.image: Optional[bytes] = image
            self.grid_reference: Optional[str] = grid_reference

        # A room belongs to a world
        self.world: "World" = world

        logger.info(f"Creating room {self.name}")
