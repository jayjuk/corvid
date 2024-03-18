from os import environ, remove, makedirs, path
from shutil import copy2
import sqlite3
import json
from logger import setup_logger
from dotenv import load_dotenv
from azure.core.credentials import AzureNamedKeyCredential
from azure.storage.blob import BlobServiceClient
from datetime import datetime

# Set up logger
logger = setup_logger()


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
            self.table_service_client = None
            self.blob_service_client = None
            self.image_container_name = None

        if not self.table_service_client and not image_only:
            logger.warning(
                "Could not get Azure table service client, data storage will be local"
            )
            # Local setup
            self.setup_local_sqlite()

        if not self.blob_service_client:
            logger.warning(
                "Could not get Azure image service client, images will be disabled"
            )

    def cloud_tables_enabled(self):
        return self.credential and self.table_service_client

    def cloud_blobs_enabled(self):
        return self.credential and self.blob_service_client

    def setup_local_sqlite(self):
        # Set up or default the SQLITE env variable
        if not environ.get("SQLITE_LOCAL_DB_PATH"):
            load_dotenv()
        self.sqlite_local_db_path = (
            environ.get("SQLITE_LOCAL_DB_PATH") or "gameserver.db"
        )

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
        from azure.data.tables import TableServiceClient

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

    # For now stateless as storage is infrequent
    def get_local_db_connection(self):
        return sqlite3.connect(self.sqlite_local_db_path)

    # Back up - used by utilities
    def backup_local_db(self):
        # Back up file with datestamp
        datestamp = datetime.now().strftime("%Y%m%d")
        backup_file = f"{self.sqlite_local_db_path}.backup.{datestamp}"
        logger.info(f"Backing up local DB to {backup_file}")
        copy2(self.sqlite_local_db_path, backup_file)

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
        exits_insert_sql = "INSERT INTO exits VALUES (?,?,?)"
        for direction in new_room["exits"]:
            c.execute(
                exits_insert_sql,
                (new_room["name"], direction, new_room["exits"][direction]),
            )

        # Store the new exit to the new room
        c.execute(
            exits_insert_sql,
            (changed_room, new_exit_direction, new_room["name"]),
        )
        c.close()

        conn.commit()
        conn.close()

    # Function to delete room locally
    def delete_room_locally(self, room_name):
        # Check if schema exists, if not create it
        conn = self.get_local_db_connection()
        self.create_sql_schema(conn)

        # Delete room and exits
        c = conn.cursor()
        c.execute("DELETE FROM rooms WHERE name=?", (room_name,))
        c.execute("DELETE FROM exits WHERE room=?", (room_name,))
        # Also delete where direction is this room
        c.execute("DELETE FROM exits WHERE destination=?", (room_name,))
        c.close()
        logger.info(f"Deleted room {room_name} from local storage, if it was there.")

        conn.commit()
        conn.close()

    def check_rowkey(self, table_client, query_filter_rowkey):
        parameters = {"pk": "jaysgame", "rk": query_filter_rowkey}
        query_filter = "PartitionKey eq @pk and RowKey eq @rk"
        for _ in table_client.query_entities(query_filter, parameters=parameters):
            return True
        return False

    def save_image_on_cloud(self, image_name, image_data):
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
    def save_image(self, file_name, image_data):
        if file_name:
            # For now, only cloud storage
            self.save_image_on_cloud(file_name, image_data)
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

    def save_new_room_on_cloud(self, new_room, new_exit_direction, changed_room):
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
    def delete_room_on_cloud(self, room_name):
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

    # Store the rooms from the dict format in the database
    def store_rooms(self, rooms, new_room_name, changed_room, new_exit_direction):
        new_room = rooms[new_room_name]
        logger.info(
            f"Storing new room {new_room['name']} and adding exit {new_exit_direction} to {changed_room}"
        )
        if self.cloud_tables_enabled():
            self.save_new_room_on_cloud(new_room, new_exit_direction, changed_room)
        else:
            self.save_new_room_locally(new_room, new_exit_direction, changed_room)

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
                logger.warning("No exits found in cloud")
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
        if self.cloud_tables_enabled():
            logger.info("Sourcing rooms from cloud")
            rooms = self.get_rooms_from_cloud()
            if rooms:
                return rooms
            logger.warning("No rooms found in cloud")
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
