import os
import sqlite3
import json
from logger import setup_logger
from object import Object
from dotenv import load_dotenv
import sys
from azure.core.credentials import AzureNamedKeyCredential
from azure.data.tables import TableServiceClient
from azure.storage.blob import BlobServiceClient

# Set up logger
logger = setup_logger()


class StorageManager:

    # Singleton constructor
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "instance"):
            cls.instance = super(StorageManager, cls).__new__(cls)
            cls.instance.__initialized = False
        return cls.instance

    # Constructor
    def __init__(self):
        if self.__initialized:
            return
        self.__initialized = True
        self.sas_token_expiry_time = None
        self.sas_token = None

        self.credential = self.get_azure_credential()

        # Get Azure storage client
        self.blob_service_client = BlobServiceClient(
            account_url="https://"
            + os.environ.get("AZURE_STORAGE_ACCOUNT_NAME")
            + ".blob.core.windows.net",
            credential=self.credential,
        )
        self.image_container_name = "jaysgameimages"

    # Utility to check env variable is set
    def check_env_var(self, var_name):
        if not os.environ.get(var_name):
            logger.info(f"ERROR: {var_name} not set. Exiting.")
            sys.exit(1)

    # Return Azure credential
    def get_azure_credential(self):
        # TODO: error handling
        if not os.environ.get("AZURE_STORAGE_ACCOUNT_NAME"):
            load_dotenv()
        self.check_env_var("AZURE_STORAGE_ACCOUNT_NAME")
        self.check_env_var("AZURE_STORAGE_ACCOUNT_KEY")
        return AzureNamedKeyCredential(
            os.environ.get("AZURE_STORAGE_ACCOUNT_NAME"),
            os.environ.get("AZURE_STORAGE_ACCOUNT_KEY"),
        )

    # Return Azure table service client
    # Assumes if we have a credential, we have AZURE_STORAGE_ACCOUNT_NAME set
    def get_azure_storage_service_client(self, credential):
        return TableServiceClient(
            endpoint="https://"
            + os.environ.get("AZURE_STORAGE_ACCOUNT_NAME")
            + ".table.core.windows.net/",
            credential=credential,
        )

    # For now stateless as storage is infrequent
    def get_local_db_connection(self):
        return sqlite3.connect("gameserver.db")

    # Create the schema if it doesn't exist
    def create_sql_schema(self, conn_in=None):
        if conn_in:
            conn = conn_in
        else:
            conn = self.get_local_db_connection()
        # Check if schema exists, if not create it
        c = conn.cursor()
        c.execute(
            """CREATE TABLE IF NOT EXISTS rooms
                    (name text, description text, image text)"""
        )
        # Create index on name
        c.execute("CREATE INDEX IF NOT EXISTS room_name ON rooms (name)")

        # Create child of rooms table to store the exits per room
        c.execute(
            """CREATE TABLE IF NOT EXISTS exits
                    (room text, direction text, destination text)"""
        )
        c.close()

        conn.commit()
        # Only close if not passed in
        if not conn_in:
            conn.close()

    def save_new_room_locally(self, new_room, new_exit_direction, changed_room):
        # Check if schema exists, if not create it
        conn = self.get_local_db_connection()
        self.create_sql_schema(conn)

        # Store new room and exits
        c = conn.cursor()
        c.execute(
            "INSERT INTO rooms VALUES (?,?,?)",
            (new_room["name"], new_room["description"], new_room["image"]),
        )
        for direction in new_room["exits"]:
            c.execute(
                "INSERT INTO exits VALUES (?,?,?)",
                (new_room["name"], direction, new_room["exits"][direction]),
            )

        # Store the new exit to the new room
        c.execute(
            "INSERT INTO exits VALUES (?,?,?)",
            (changed_room, new_exit_direction, new_room["name"]),
        )
        c.close()

        conn.commit()
        conn.close()

    def check_rowkey(self, table_client, query_filter_rowkey):
        parameters = {"pk": "jaysgame", "rk": query_filter_rowkey}
        query_filter = "PartitionKey eq @pk and RowKey eq @rk"
        for row in table_client.query_entities(query_filter, parameters=parameters):
            return True
        return False

    def save_image_on_cloud(self, image_name):

        logger.info(f"Uploading image '{image_name}' to cloud")

        # Get a reference to the container
        container_client = self.blob_service_client.get_container_client(
            self.image_container_name
        )

        # Create the container if it doesn't exist
        try:
            container_client.create_container()
            logger.info(f"Created container '{self.image_container_name}'")
        except:
            logger.error(f"Container '{self.image_container_name}' already exists")

        # Get a reference to the blob
        blob_client = self.blob_service_client.get_blob_client(
            self.image_container_name, image_name
        )

        # Upload the image
        with open(image_name, "rb") as data:
            try:
                blob_client.upload_blob(data)
                logger.info(f"Uploaded image '{image_name}'")
                # Delete the image from the local directory
                os.remove(image_name)
            except:
                logger.error(f"Container '{image_name}' already exists")

    # External function for the world class to use, world doesn't need to know about cloud etc
    def save_image(self, file_name):
        # For now, only cloud storage
        self.save_image_on_cloud(file_name)
        # Move file name to full path
        return True

    # def generate_sas_url(
    #     self,
    #     blob_name: str,
    # ):
    #     # Check expiry time
    #     if not (
    #         self.sas_token
    #         and self.sas_token_expiry_time
    #         # 5 minutes before expiry
    #         and self.sas_token_expiry_time > datetime.utcnow() + timedelta(minutes=5)
    #     ):
    #         logger.info(f"Refreshing SAS token")
    #         # Refresh token
    #         self.sas_token = generate_blob_sas(
    #             account_name=self.blob_service_client.account_name,
    #             container_name=self.image_container_name,
    #             blob_name=blob_name,
    #             account_key=self.blob_service_client.credential.account_key,
    #             permission=BlobSasPermissions(read=True),
    #             expiry=datetime.utcnow() + timedelta(hours=1),
    #         )
    #     return f"https://{self.blob_service_client.account_name}.blob.core.windows.net/{self.image_container_name}/{blob_name}?{self.sas_token}"

    def get_image_url(self, image_name):
        logger.info(f"Resolving image URL for image {image_name}")
        hostname = os.environ.get("GAMESERVER_HOSTNAME") or "localhost"
        # TODO: 5000 is hardcoded
        return "http://" + hostname + ":5000/image/" + image_name

    def save_new_room_on_cloud(self, new_room, new_exit_direction, changed_room):
        # Get Azure storage client
        credential = self.get_azure_credential()
        service_client = self.get_azure_storage_service_client(credential)
        rooms_client = service_client.create_table_if_not_exists("rooms")

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
            logger.warn(f"Room {new_room['name']} already stored")

        exits_client = service_client.create_table_if_not_exists("exits")
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
                logger.warn(f"Exit {exit_dict['RowKey']} already stored")

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
            logger.warn(f"Exit {exit_dict['RowKey']} already stored")

    # Store the rooms from the dict format in the database
    def store_rooms(self, rooms, new_room_name, changed_room, new_exit_direction):
        new_room = rooms[new_room_name]
        logger.info(
            f"Storing new room {new_room['name']} and adding exit {new_exit_direction} to {changed_room}"
        )
        # Save room both locally and in cloud
        self.save_new_room_locally(new_room, new_exit_direction, changed_room)
        self.save_new_room_on_cloud(new_room, new_exit_direction, changed_room)

        # Check subfolder exists for saving user generated maps
        # TODO: for now this is saving every version, and this is really just a temporary backup
        user_map_folder_path = "user_maps"
        os.makedirs(user_map_folder_path, exist_ok=True)
        with open(
            user_map_folder_path + os.sep + ".user_generated_map_backup.tmp",
            "w",
        ) as f:
            json.dump(rooms, f, indent=4)

    # Check if the schema exists but don't create if not
    # Handle that the connection may not exist
    def check_schema(self):
        conn = self.get_local_db_connection()
        if not conn:
            return False
        c = conn.cursor()
        # Check if schema exists, if not create it
        c.execute(
            """SELECT name FROM sqlite_master WHERE type='table' AND name='rooms'"""
        )
        schema_exists = c.fetchone()
        conn.close()
        return schema_exists

    def cloud_enabled(self):
        try:
            self.get_azure_storage_service_client(self.get_azure_credential())
            return True
        except:
            return False

    def get_rooms_from_cloud(self):
        # Get Azure storage client
        credential = self.get_azure_credential()
        service_client = self.get_azure_storage_service_client(credential)
        rooms_client = service_client.get_table_client("rooms")
        if rooms_client:
            rooms = {}
            for entity in rooms_client.query_entities(""):
                rooms[entity["RowKey"]] = {
                    "name": entity["RowKey"],
                    "description": entity["description"],
                    "image": entity["image"],
                    "exits": {},
                }
            exits_client = service_client.get_table_client("exits")
            if exits_client:
                for entity in exits_client.query_entities(""):
                    rooms[entity["room"]]["exits"][entity["direction"]] = entity[
                        "destination"
                    ]
                return rooms
            else:
                logger.warn("No exits found in cloud")
        return None

    def get_rooms_from_local_db(self):
        conn = self.get_local_db_connection()
        # Check schema
        if conn is None or not self.check_schema():
            return self.get_default_rooms()
        # Get rooms and exits
        c = conn.cursor()
        c.execute("SELECT * FROM rooms")
        rooms = c.fetchall()
        c.execute("SELECT * FROM exits")
        exits = c.fetchall()
        # Convert to dict
        rooms_dict = {}
        for room in rooms:
            rooms_dict[room[0]] = {
                "name": room[0],
                "description": room[1],
                "image": room[2],
                "exits": {},
            }
        for exit in exits:
            rooms_dict[exit[0]]["exits"][exit[1]] = exit[2]
        conn.close()
        if not rooms:
            return self.get_default_rooms()
        return rooms_dict

    # Get rooms and return in the dict format expected by the game server
    def get_rooms(self):
        # Try cloud first
        if self.cloud_enabled():
            logger.info("Sourcing rooms from cloud")
            rooms = self.get_rooms_from_cloud()
            if rooms:
                return rooms
            logger.warn("No rooms found in cloud")
        # Fall back to local db
        logger.info("Sourcing rooms from local DB")
        return self.get_rooms_from_local_db()

    def get_default_rooms(self):
        # This is the built-in static rooms file
        default_map_file = "map.json"
        with open(default_map_file, "r") as f:
            rooms = json.load(f)
        # Add room name to each room
        for room in rooms:
            rooms[room]["name"] = room
        return rooms

    # This is only called from a setup script
    def store_default_rooms(self):
        # This is the built-in static rooms file
        default_map_file = "map.json"
        with open(default_map_file, "r") as f:
            rooms = json.load(f)
        # Check if schema exists, if not create it
        self.create_sql_schema()
        conn = self.get_local_db_connection()
        c = conn.cursor()

        for room in rooms:
            # Store room and exits
            c.execute(
                "INSERT INTO rooms VALUES (?,?,?)",
                (room, rooms[room]["description"], rooms[room]["image"]),
            )
            for direction in rooms[room]["exits"]:
                c.execute(
                    "INSERT INTO exits VALUES (?,?,?)",
                    (room, direction, rooms[room]["exits"][direction]),
                )
        logger.info("Stored default rooms")
        conn.commit()
        conn.close()


# Main runs store default rooms
if __name__ == "__main__":
    storage_manager = StorageManager()
    storage_manager.store_default_rooms()
