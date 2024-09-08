from typing import Any, Dict, List, Optional, Union
from logger import setup_logger, exit
from utils import get_critical_env_variable
import json
from os import path, makedirs

# Set up logger
logger = setup_logger()


# Superclass for storage managers
class StorageManager:

    # Constructor
    def __init__(self, image_only: bool = False) -> None:
        # Cache of data types to convert to/from JSON to strings when storing
        self.complex_variable_cache: Dict[str, List[str]] = {}

    def store_image(
        self, world_name: str, file_name: Optional[str], image_data: Any
    ) -> Union[bool, None]:
        if file_name:
            # For now, only cloud storage
            return self.store_image_in_cloud(world_name, file_name, image_data)
        else:
            logger.error("Missing file name, cannot store")

    def store_image_in_cloud(
        self, world_name: str, image_name: str, image_data: Any
    ) -> bool:
        logger.info(
            f"Abstract method - does not return image: {world_name}, {image_name}"
        )
        return False

    def get_image_url(self, world_name: str, image_name: str) -> Optional[str]:
        if image_name:
            logger.info(
                f"Resolving image URL for world {world_name} / image {image_name}"
            )
            hostname = get_critical_env_variable("IMAGESERVER_HOSTNAME")
            port = get_critical_env_variable("IMAGESERVER_PORT")
            return f"http://{hostname}:{port}/image/{self.get_blob_name(world_name, image_name)}"
        return None

    def get_blob_name(self, world_name: str, image_name: str) -> str:
        # Black is a special image that needs no prefix, it is not created by AI or specific to a world.
        # It is for starting from an empty world.
        # So check if image name start with 'black.'
        if image_name.startswith("black."):
            return image_name
        if world_name:
            return world_name + "." + image_name
        return image_name

    def get_image_blob(self, blob_name: str) -> Optional[Any]:
        logger.info(f"Abstract method - does not return image: {blob_name}")
        return None

    def get_default_world_data(
        self, world_name: str, object_type: str
    ) -> Dict[str, Any]:
        full_path = path.join("world_data", world_name, f"{object_type.lower()}.json")
        if not path.exists(full_path):
            full_path = path.join("world_data", "empty", f"{object_type.lower()}.json")
            if not path.exists(full_path):
                exit(logger, f"Default data file not found: {full_path}")
        with open(full_path, "r") as f:
            default_data = json.load(f)
        return default_data

    def check_complex_variable_cache(self, entity: Dict[str, Any]) -> None:
        if entity["PartitionKey"] not in self.complex_variable_cache:
            self.complex_variable_cache[entity["PartitionKey"]] = []
            for key, value in entity.items():
                if isinstance(value, (list, dict)) or (
                    isinstance(value, str)
                    and len(value) > 1
                    and (
                        (value[0] == "[" and value[-1] == "]")
                        or (value[0] == "{" and value[-1] == "}")
                    )
                ):
                    self.complex_variable_cache[entity["PartitionKey"]].append(key)

    def stringify_object(
        self, entity: Dict[str, Any], action: str = "stringify"
    ) -> None:
        self.check_complex_variable_cache(entity)
        for variable in self.complex_variable_cache[entity["PartitionKey"]]:
            if variable in entity:
                if action == "stringify":
                    entity[variable] = json.dumps(entity[variable])
                else:  # destringify
                    entity[variable] = json.loads(entity[variable])

    def store_game_objects(
        self, world_name: str, objects: List[Dict[str, Any]]
    ) -> None:
        logger.info("Storing all Python objects")
        for object in objects:
            self.store_game_object(world_name, object)

    def get_game_object(
        self, game_name: str, object_type: str, rowkey_value: str
    ) -> Dict[str, Any]:
        for object in self.get_game_objects(game_name, object_type, rowkey_value):
            return object

    def store_game_object(self, world_name: str, object: object) -> None:
        # Unit testing will use this superclass method hence not abstract
        logger.info(
            f"NOT storing python object in game {world_name}: {object.__dict__}"
        )
        return True

    def delete_game_object(
        self, world_name: str, object_type: str, name: str, location: str
    ) -> bool:
        # Unit testing will use this superclass method hence not abstract
        logger.info(
            f"NOT deleting python object in game {world_name}: {object.__dict__}"
        )
        return False

    def get_game_objects(
        self, world_name: str, object_type: str, rowkey_value: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        # Unit testing will use this superclass method hence not abstract
        logger.info(f"NOT getting python objects in game {world_name}: {object_type}")
        return []
