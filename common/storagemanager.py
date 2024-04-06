from os import environ, remove, makedirs, path
from shutil import copy2
import sqlite3
import json
from logger import setup_logger, exit, debug
from azure.core.credentials import AzureNamedKeyCredential
from azure.storage.blob import BlobServiceClient
from azure.data.tables import TableServiceClient, UpdateMode
from datetime import datetime
import sys

# Set up logger
logger = setup_logger()

# Superclass for storage managers
class StorageManager:

    # Constructor
    def __init__(self, image_only=False):
        # Cache of data types to convert to/from JSON to strings when storing
        self.complex_variable_cache = {}

    # External function for the world class to use, world doesn't need to know about cloud etc
    def store_image(self, world_name, file_name, image_data):
        if file_name:
            # For now, only cloud storage
            return self.store_image_in_cloud(world_name, file_name, image_data)
        else:
            logger.error("Missing file name, cannot store")

    def store_image_in_cloud(self, world_name, image_name, image_data):
        logger.info(
            f"Abstract method - does not return image: {world_name}, {image_name}"
        )
        return False

    def get_image_url(self, world_name, image_name):
        if image_name:
            logger.info(
                f"Resolving image URL for world {world_name} / image {image_name}"
            )
            hostname = environ["IMAGESERVER_HOSTNAME"]
            port = environ["IMAGESERVER_PORT"]
            return f"http://{hostname}:{port}/image/{self.get_blob_name(world_name, image_name)}"
        return None

    def get_blob_name(self, world_name, image_name):
        if world_name:
            return world_name + "." + image_name
        return image_name

    # External function for the world class to use, world doesn't need to know about cloud etc
    def get_image_blob(self, blob_name):
        logger.info(f"Abstract method - does not return image: {blob_name}")
        return None

    # Resolve path for static data a given object type
    def get_default_world_data(self, world_name, object_type):
        full_path = path.join("world_data", world_name, f"{object_type.lower()}.json")
        with open(full_path, "r") as f:
            default_data = json.load(f)
        return default_data

    # Learn the list of variables containing dicts and strings for a type of object
    def check_complex_variable_cache(self, entity):
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

    # Turn lists and dicts into strings and back again
    def stringify_object(self, entity, action="stringify"):
        self.check_complex_variable_cache(entity)
        for variable in self.complex_variable_cache[entity["PartitionKey"]]:
            if variable in entity:
                if action == "stringify":
                    entity[variable] = json.dumps(entity[variable])
                else:  # destringify
                    entity[variable] = json.loads(entity[variable])

    # Store all Python objects (expects list of object dicts)
    def store_game_objects(self, world_name, objects):
        logger.info("Storing all Python objects")
        for object in objects:
            self.store_game_object(world_name, object)

    # Store all Python objects, received as actual objects
    def store_game_object(self, game_name, object):
        logger.info(
            f"Abstract method - NOT storing python object '{object.__dict__.get('name','')}' in game {game_name}"
        )

    # Returns all instances of a type of object, as a dict
    def get_game_objects(self, world_name, object_type, rowkey_value=None):
        logger.info(
            f"Abstract method - NOT getting objects of type '{object_type}' for game {world_name} and rowkey value {rowkey_value}"
        )
        return []

    # Explicitly get one object by its key
    def get_game_object(self, game_name, object_type, rowkey_value):
        for object in self.get_game_objects(game_name, object_type, rowkey_value):
            return object
