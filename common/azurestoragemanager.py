from storagemanager import StorageManager
from shutil import copy2
from logger import setup_logger, exit, debug
from azure.core.credentials import AzureNamedKeyCredential
from azure.storage.blob import BlobServiceClient, ContainerClient
from azure.data.tables import TableServiceClient, UpdateMode
from utils import get_critical_env_variable
from typing import Optional, Dict, List, Any

# Set up logger
logger = setup_logger()

# This is for Azure
import logging


class AzureStorageManager(StorageManager):

    # Constructor
    def __init__(self, image_only: bool = False) -> None:
        # Call parent constructor
        super().__init__(image_only)
        # Get and remember credential
        self.credential: Optional[AzureNamedKeyCredential] = self.get_azure_credential()
        if self.credential:
            # Get Azure storage client
            if image_only:
                self.table_service_client: Optional[TableServiceClient] = None
                logger.info("Running in images only mode - no table storage")
            else:
                self.table_service_client: Optional[TableServiceClient] = (
                    self.get_azure_table_service_client()
                )

            # Get Azure storage client
            self.blob_service_client: Optional[BlobServiceClient] = (
                self.get_azure_blob_service_client()
            )
            self.image_container_name: str = "jaysgameimages"
        else:
            exit(logger, "Could not get Azure credential.")

        if not self.table_service_client and not image_only:
            exit(logger, "Could not get Azure table service client.")

        if not self.blob_service_client:
            exit(logger, "Could not get Azure image service client.")

        # Set the log level to WARNING to suppress INFO and DEBUG logs
        logging.getLogger("azure").setLevel(logging.WARNING)

        # Cache of data types to convert to/from JSON to strings when storing
        self.complex_variable_cache: dict = {}

    # Return Azure table service client
    # Assumes if we have a credential, we have AZURE_STORAGE_ACCOUNT_NAME set
    def get_azure_table_service_client(self) -> TableServiceClient:

        return TableServiceClient(
            endpoint="https://"
            + get_critical_env_variable("AZURE_STORAGE_ACCOUNT_NAME")
            + ".table.core.windows.net/",
            credential=self.credential,
        )

    def get_azure_blob_service_client(self) -> BlobServiceClient:
        return BlobServiceClient(
            account_url="https://"
            + get_critical_env_variable("AZURE_STORAGE_ACCOUNT_NAME")
            + ".blob.core.windows.net",
            credential=self.credential,
        )

    def check_rowkey(
        self, table_client: TableServiceClient, query_filter_rowkey: str
    ) -> bool:
        parameters: dict = {"pk": "jaysgame", "rk": query_filter_rowkey}
        query_filter: str = "PartitionKey eq @pk and RowKey eq @rk"
        for _ in table_client.query_entities(query_filter, parameters=parameters):
            return True
        return False

    def store_image_in_cloud(
        self, world_name: str, image_name: str, image_data: bytes
    ) -> bool:
        logger.info(f"Uploading image '{image_name}' to cloud")

        # Get a reference to the container
        container_client: Optional[ContainerClient] = (
            self.blob_service_client.get_container_client(self.image_container_name)
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

    def get_image_url(self, world_name: str, image_name: str) -> Optional[str]:
        if image_name:
            logger.info(
                f"Resolving image URL for world {world_name} / image {image_name}"
            )
            hostname: str = get_critical_env_variable("IMAGESERVER_HOSTNAME")
            port: str = get_critical_env_variable("IMAGESERVER_PORT")
            return f"http://{hostname}:{port}/image/{self.get_blob_name(world_name, image_name)}"
        return None

    def get_image_blob(self, blob_name: str) -> Optional[bytes]:
        if self.image_container_name:
            logger.info(f"Downloading {blob_name} from Azure blob storage")
            blob_client: BlobServiceClient = self.blob_service_client.get_blob_client(
                self.image_container_name, blob_name
            )
            if blob_client:
                return blob_client.download_blob().readall()
            else:
                logger.error("Could not resolve blob client.")
        return None

    # Store all Python objects, received as actual objects
    def store_game_object(self, game_name: str, object: object) -> bool:
        logger.debug(f"Storing python object in game {game_name}: {object.__dict__}")

        objects_client = self.table_service_client.create_table_if_not_exists(
            "PythonObjects"
        )

        # Store object in Azure
        # Convert to dict
        entity: dict = object.__dict__.copy()
        entity["PartitionKey"] = game_name + "__" + type(object).__name__

        # Don't store objects named "system" - they are transient
        if entity["name"] == "system":
            return False

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
        # 3. Input history - not needed, we want to start fresh each session
        if "input_history" in entity:
            del entity["input_history"]
        # Convert fields containing lists/dicts to strings
        # This keeps the database readable/editable, simple, and cheap (can use Azure Table Storage in other words)

        # First, learn and cache the list of fields to convert for this type of object (partition key can be used for this)
        self.stringify_object(entity)

        logger.info(f"Storing {entity['name']}")
        objects_client.upsert_entity(mode=UpdateMode.REPLACE, entity=entity)

        # Return true if successful
        return True

    # Returns all instances of a type of object, as a dict
    def get_game_objects(
        self, world_name: str, object_type: str, rowkey_value: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        objects_client = self.table_service_client.get_table_client("PythonObjects")
        if objects_client:
            objects: List[Dict[str, Any]] = []
            parameters: Dict[str, str] = {"pk": world_name + "__" + object_type}
            query_filter: str = "PartitionKey eq @pk"
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
