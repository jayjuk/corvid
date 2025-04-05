from typing import Dict, Optional, Any
from utils import set_up_logger, exit

# Set up logger
logger = set_up_logger()


# Person class
class Room:

    def __init__(
        self,
        world: "World",
        name: Optional[str] = None,
        description: Optional[str] = None,
        exits: Optional[Dict[str, str]] = None,
        init_dict: Optional[Dict[str, Any]] = None,
        creator: Optional[str] = None,
        image: Optional[str] = None,
        grid_reference: Optional[str] = None,
    ) -> None:
        if init_dict:
            self.__dict__.update(init_dict)
            # Create blank image if not provided
            if not hasattr(self, "image"):
                self.image = None
        else:
            self.name: Optional[str] = name
            self.description: Optional[str] = description
            self.exits: Optional[Dict[str, str]] = exits
            self.creator: Optional[str] = creator
            self.image: Optional[str] = image
            self.grid_reference: Optional[str] = grid_reference

        # A room belongs to a world
        self.world: "World" = world

        logger.debug(f"Creating room {self.name}")
