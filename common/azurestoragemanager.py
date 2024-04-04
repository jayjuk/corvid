from storagemanager import StorageManager
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

# This is for Azure
import logging


class AzureStorageManager(StorageManager):

    # Constructor
    def __init__(self, image_only=False):
        super().__init__(image_only)
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
            self.image_container_name = "jaysgameimages"
        else:
            exit(logger, "Could not get Azure credential.")

        if not self.table_service_client and not image_only:
            exit(logger, "Could not get Azure table service client.")

        if not self.blob_service_client:
            exit(logger, "Could not get Azure image service client.")

        # Set the log level to WARNING to suppress INFO and DEBUG logs
        logging.getLogger("azure").setLevel(logging.WARNING)

        # Cache of data types to convert to/from JSON to strings when storing
        self.complex_variable_cache = {}

    # Utility to check env variable is set
    def check_env_var(self, var_name):
        if not environ.get(var_name):
            exit(f"{var_name} not set.")
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

    def store_image_in_cloud(self, world_name, image_name, image_data):
        if self.cloud_blobs_enabled():
            logger.info(f"Uploading image '{image_name}' to cloud")

            # Get a reference to the container
            container_client = self.blob_service_client.get_container_client(
                self.image_container_name
            )

            # Create the container if it doesn't exist
            if not container_client:
                try:
                    container_client.create_container()
                    logger.info(f"Created container '{self.image_container_name}'")
                except Exception as e:
                    logger.error(
                        f"Container '{self.image_container_name}' already exists: {e}"
                    )

            # Get a reference to the blob
            blob_client = self.blob_service_client.get_blob_client(
                self.image_container_name, self.get_blob_name(world_name, image_name)
            )

            # Upload the image
            try:
                blob_client.upload_blob(image_data)
                logger.info(f"Uploaded image '{image_name}'")
                return True
            except Exception as e:
                logger.error(f"Error uploading image: {e}")
            return False
        else:
            logger.warning(
                f"Not uploading image '{image_name}' to cloud as storage not enabled."
            )

    def get_image_url(self, world_name, image_name):
        if image_name:
            logger.info(
                f"Resolving image URL for world {world_name} / image {image_name}"
            )
            hostname = environ["IMAGESERVER_HOSTNAME"]
            port = environ["IMAGESERVER_PORT"]
            return f"http://{hostname}:{port}/image/{self.get_blob_name(world_name, image_name)}"
        return None

    def get_image_blob(self, blob_name):
        if self.cloud_blobs_enabled() and self.image_container_name:
            logger.info(f"Downloading {blob_name} from Azure blob storage")
            blob_client = self.blob_service_client.get_blob_client(
                self.image_container_name, blob_name
            )
            if blob_client:
                return blob_client.download_blob().readall()
            else:
                logger.error("Could not resolve blob client.")
        return None

    # Store all Python objects, received as actual objects
    def store_game_object(self, game_name, object):
        logger.debug(f"Storing python object in game {game_name}: {object.__dict__}")

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

        # TODO #85 Don't hard-code attributes to remove on storage
        # Override fields that contain object values lists etc

        # 1. World - use the game/world name just for supportability
        entity["world"] = game_name
        # 2. Inventory - reconstituted from location
        if "inventory" in entity:
            del entity["inventory"]
        # Convert fields containing lists/dicts to strings
        # This keeps the database readable/editable, simple, and cheap (can use Azure Table Storage in other words)

        # First, learn and cache the list of fields to convert for this type of object (partition key can be used for this)
        self.stringify_object(entity)

        logger.info(f"Storing {entity['name']}")
        objects_client.upsert_entity(mode=UpdateMode.REPLACE, entity=entity)

    # Returns all instances of a type of object, as a dict
    def get_game_objects(self, world_name, object_type, rowkey_value=None):
        objects_client = self.table_service_client.get_table_client("PythonObjects")
        if objects_client:
            objects = []
            parameters = {"pk": world_name + "__" + object_type}
            query_filter = "PartitionKey eq @pk"
            if rowkey_value:
                parameters["rk"] = rowkey_value
                query_filter += " and RowKey eq @rk"
            for entity in objects_client.query_entities(
                query_filter, parameters=parameters
            ):
                self.stringify_object(entity, action="destringify")
                objects.append(entity.copy())
            return objects
        exit(logger, "No objects found in cloud!")
