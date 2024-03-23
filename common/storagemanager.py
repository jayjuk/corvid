from os import environ, remove, makedirs, path
from shutil import copy2
import sqlite3
import json
from logger import setup_logger, exit
from dotenv import load_dotenv
from azure.core.credentials import AzureNamedKeyCredential
from azure.storage.blob import BlobServiceClient
from azure.data.tables import TableServiceClient, UpdateMode
from datetime import datetime
import sys

# Set up logger
logger = setup_logger()

# This is for Azure
import logging


class StorageManager:

    # Constructor
    def __init__(self, image_only=False, image_container_name="jaysgameimages"):
        self.sas_token_expiry_time = None
        self.sas_token = None

        # Get and remember credential
        self.credential = self.get_azure_credential()
        if self.credential:
            # Get Azure storage client
            if image_only:
                self.table_service_client = None
                logger.info("Running in images only mode - no table storage")
            else:
                self.table_service_client = self.get_azure_table_service_client()

            # Get Azure storage client
            self.blob_service_client = self.get_azure_blob_service_client()
            self.image_container_name = image_container_name
        else:
            exit(logger, "Could not get Azure credential.")

        if not self.table_service_client and not image_only:
            exit(logger, "Could not get Azure table service client.")

        if not self.blob_service_client:
            exit(logger, "Could not get Azure image service client.")

        # Set the log level to WARNING to suppress INFO and DEBUG logs
        logging.getLogger("azure").setLevel(logging.WARNING)

    def cloud_tables_enabled(self):
        return self.credential and self.table_service_client

    def cloud_blobs_enabled(self):
        return self.credential and self.blob_service_client

    # Utility to check env variable is set
    def check_env_var(self, var_name):
        if not environ.get(var_name):
            logger.warning(f"{var_name} not set.")
        return environ.get(var_name, "")

    # Return Azure credential
    def get_azure_credential(self):
        if self.check_env_var("AZURE_STORAGE_ACCOUNT_NAME") and self.check_env_var(
            "AZURE_STORAGE_ACCOUNT_KEY"
        ):
            return AzureNamedKeyCredential(
                environ.get("AZURE_STORAGE_ACCOUNT_NAME"),
                environ.get("AZURE_STORAGE_ACCOUNT_KEY"),
            )
        else:
            return None

    # Return Azure table service client
    # Assumes if we have a credential, we have AZURE_STORAGE_ACCOUNT_NAME set
    def get_azure_table_service_client(self):

        return TableServiceClient(
            endpoint="https://"
            + environ.get("AZURE_STORAGE_ACCOUNT_NAME")
            + ".table.core.windows.net/",
            credential=self.credential,
        )

    def get_azure_blob_service_client(self):
        return BlobServiceClient(
            account_url="https://"
            + environ.get("AZURE_STORAGE_ACCOUNT_NAME")
            + ".blob.core.windows.net",
            credential=self.credential,
        )

    def check_rowkey(self, table_client, query_filter_rowkey):
        parameters = {"pk": "jaysgame", "rk": query_filter_rowkey}
        query_filter = "PartitionKey eq @pk and RowKey eq @rk"
        for _ in table_client.query_entities(query_filter, parameters=parameters):
            return True
        return False

    def store_image_in_cloud(self, image_name, image_data):
        if self.cloud_blobs_enabled():
            logger.info(f"Uploading image '{image_name}' to cloud")

            # Get a reference to the container
            container_client = self.blob_service_client.get_container_client(
                self.image_container_name
            )

            # Create the container if it doesn't exist
            try:
                container_client.create_container()
                logger.info(f"Created container '{self.image_container_name}'")
            except Exception as e:
                logger.error(
                    f"Container '{self.image_container_name}' already exists: {e}"
                )

            # Get a reference to the blob
            blob_client = self.blob_service_client.get_blob_client(
                self.image_container_name, image_name
            )

            # Upload the image
            try:
                blob_client.upload_blob(image_data)
                logger.info(f"Uploaded image '{image_name}'")
            except Exception as e:
                logger.error(f"Error uploading image: {e}")
        else:
            logger.warning(
                f"Not uploading image '{image_name}' to cloud as storage not enabled."
            )

    # External function for the world class to use, world doesn't need to know about cloud etc
    def store_image(self, file_name, image_data):
        if file_name:
            # For now, only cloud storage
            self.store_image_in_cloud(file_name, image_data)
            # Move file name to full path
            return True
        else:
            logger.error("Missing file name, cannot upload")

    def get_image_url(self, image_name):
        if image_name:
            logger.info(f"Resolving image URL for image {image_name}")
            hostname = environ["IMAGESERVER_HOSTNAME"]
            port = environ["IMAGESERVER_PORT"]
            return f"http://{hostname}:{port}/image/{image_name}"
        return None

    def get_image_blob(self, image_name):
        if self.cloud_blobs_enabled() and self.image_container_name:
            logger.info(f"Downloading {image_name} from Azure blob storage")
            blob_client = self.blob_service_client.get_blob_client(
                self.image_container_name, image_name
            )
            if blob_client:
                return blob_client.download_blob().readall()
            else:
                logger.error("Could not resolve blob client.")
        return None

    # Store the rooms from the dict format in the database
    def store_room(self, rooms, new_room_name, changed_room, new_exit_direction):
        new_room = rooms[new_room_name]
        logger.info(
            f"Storing new room {new_room['name']} and adding exit {new_exit_direction} to {changed_room}"
        )
        rooms_client = self.table_service_client.create_table_if_not_exists("rooms")

        # Store room in Azure
        # First check if key exists
        if not self.check_rowkey(rooms_client, new_room["name"]):
            new_room["PartitionKey"] = "jaysgame"
            new_room["RowKey"] = new_room["name"]
            logger.info(f"Storing {new_room['name']}")
            room_only = new_room.copy()
            del room_only["exits"]
            rooms_client.create_entity(entity=room_only)
        else:
            logger.warning(f"Room {new_room['name']} already stored")

        exits_client = self.table_service_client.create_table_if_not_exists("exits")
        # Store exits in Azure
        # Should just loop once
        for direction, destination in new_room["exits"].items():
            exit_dict = {
                "PartitionKey": "jaysgame",
                "RowKey": f"{new_room['name']}_{direction}",
                "room": new_room["name"],
                "direction": direction,
                "destination": destination,
            }

            if not self.check_rowkey(exits_client, exit_dict["RowKey"]):
                logger.info(f"Storing {exit_dict['RowKey']}")
                exits_client.create_entity(entity=exit_dict)
            else:
                logger.warning(f"Exit {exit_dict['RowKey']} already stored")

        # Also save the new exit of the changed room
        exit_dict = {
            "PartitionKey": "jaysgame",
            "RowKey": f"{changed_room}_{new_exit_direction}",
            "room": changed_room,
            "direction": new_exit_direction,
            "destination": new_room["name"],
        }
        if not self.check_rowkey(exits_client, exit_dict["RowKey"]):
            logger.info(f"Storing {exit_dict['RowKey']}")
            exits_client.create_entity(entity=exit_dict)
        else:
            logger.warning(f"Exit {exit_dict['RowKey']} already stored")

    # Utility function to delete room from cloud (not used in game)
    def delete_room(self, room_name):
        rooms_client = self.table_service_client.get_table_client("rooms")
        exits_client = self.table_service_client.get_table_client("exits")

        # Delete exits from Azure
        # Should just loop once
        for direction in ["north", "east", "south", "west"]:
            exit_name = f"{room_name}_{direction}"
            if self.check_rowkey(exits_client, exit_name):
                logger.info(f"Deleting {exit_name}")
                exits_client.delete_entity(partition_key="jaysgame", row_key=exit_name)
            else:
                logger.warning(f"Exit {exit_name} not found")

        # Also delete where direction is this room
        for entity in exits_client.query_entities(f"destination eq '{room_name}'"):
            logger.info(f"Deleting {entity['RowKey']}")
            exits_client.delete_entity(
                partition_key="jaysgame", row_key=entity["RowKey"]
            )

        # Delete room from Azure
        # First check if key exists
        if self.check_rowkey(rooms_client, room_name):
            logger.info(f"Deleting {room_name}")
            rooms_client.delete_entity(partition_key="jaysgame", row_key=room_name)
        else:
            logger.warning(f"Room {room_name} not found")

    # Store all objects (expects list of object dicts)
    def store_objects(self, objects):
        logger.info("Storing all objects")
        for object in objects:
            self.store_object(object)

    # Store all objects
    def store_object(self, object):
        logger.info(f"Storing object: {object['name']}")

        objects_client = self.table_service_client.create_table_if_not_exists("objects")

        # Store object in Azure
        # First check if key exists
        if not self.check_rowkey(objects_client, object["name"]):
            object["PartitionKey"] = "jaysgame"
            object["RowKey"] = object["name"]
            logger.info(f"Storing {object['name']}")
            objects_client.create_entity(entity=object)
        else:
            logger.warning(f"Object {object['name']} already stored")

    def get_objects_from_cloud(self):
        objects_client = self.table_service_client.get_table_client("objects")
        if objects_client:
            objects = []
            for entity in objects_client.query_entities(""):
                objects.append(
                    {
                        "name": entity["RowKey"],
                        "description": entity["description"],
                        "price": entity.get("price", None),
                        "location": entity.get("starting_room", None),
                        "starting_merchant": entity.get("starting_merchant", None),
                    }
                )
            return objects
        exit(logger, "No objects found in cloud!")

    # Get objects and return in the dict format expected by the game server
    def get_objects(self):
        # Try cloud first
        logger.info("Sourcing objects from cloud")
        objects = self.get_objects_from_cloud()
        if objects:
            return objects
        # Fall back to local db
        logger.info("Sourcing objects from static file")
        return self.get_default_objects()

    def get_default_objects(self):
        with open(path.join("world_data", "starting_objects.json"), "r") as f:
            default_objects = json.load(f)
        return default_objects

    def get_rooms_from_cloud(self):
        rooms_client = self.table_service_client.get_table_client("rooms")
        if rooms_client:
            rooms = {}
            for entity in rooms_client.query_entities(""):
                rooms[entity["RowKey"]] = {
                    "name": entity["RowKey"],
                    "description": entity["description"],
                    "image": entity.get("image", None),
                    "exits": {},
                }
            exits_client = self.table_service_client.get_table_client("exits")
            if exits_client:
                for entity in exits_client.query_entities(""):
                    rooms[entity["room"]]["exits"][entity["direction"]] = entity[
                        "destination"
                    ]
                return rooms
            else:
                exit(logger, "No exits found in cloud")
        else:
            exit(logger, "No rooms found in cloud")

    # Get rooms and return in the dict format expected by the game server
    def get_rooms(self):
        # Try cloud first
        logger.info("Loading rooms from cloud")
        rooms = self.get_rooms_from_cloud()
        if rooms:
            return rooms
        logger.warning("No rooms found in cloud - loading from static")
        return self.get_default_rooms()

    def get_default_rooms(self):
        # This is the built-in static rooms file
        default_map_file = "map.json"
        with open(default_map_file, "r") as f:
            rooms = json.load(f)
        # Add room name to each room
        for room in rooms:
            rooms[room]["name"] = room
        return rooms

    # Store all Python objects (expects list of object dicts)
    def store_python_objects(self, game_name, objects):
        logger.info("Storing all Python objects")
        for object in objects:
            self.store_python_object(game_name, object)

    # Store all Python objects, received as actual objects
    def store_python_object(self, game_name, object):
        logger.info(f"Storing python object in game {game_name}: {object.__dict__}")

        objects_client = self.table_service_client.create_table_if_not_exists(
            "PythonObjects"
        )

        # Store object in Azure
        # Convert to dict
        entity = object.__dict__.copy()
        entity["PartitionKey"] = game_name + "__" + type(object).__name__
        entity["RowKey"] = entity["name"]
        if "id" in entity:
            entity["RowKey"] += "__" + entity["id"]

        # Override fields that contain object values lists etc

        # 1. World - use the game/world name just for supportability
        entity["world"] = game_name
        # 2. Inventory - reconstituted from location
        if "inventory" in entity:
            del entity["inventory"]
        # TODO: improve this
        if "actions" in entity:
            entity["actions"] = "_".join(entity["actions"])

        logger.info(f"Storing {entity['name']}")
        objects_client.upsert_entity(mode=UpdateMode.REPLACE, entity=entity)

    # Returns all instances of a type of object, as a dict
    def get_python_objects(self, game_name, object_type):
        objects_client = self.table_service_client.get_table_client("PythonObjects")
        if objects_client:
            objects = []
            parameters = {"pk": game_name + "__" + object_type}
            query_filter = "PartitionKey eq @pk"
            for entity in objects_client.query_entities(
                query_filter, parameters=parameters
            ):
                # TODO: improve this
                if "actions" in entity:
                    entity["actions"] = entity["actions"].split("_")
                objects.append(entity.copy())
            return objects
        exit(logger, "No objects found in cloud!")
