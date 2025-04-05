from azure.core.credentials import AzureNamedKeyCredential
from azure.data.tables import TableServiceClient, TableClient
from storagemanager import StorageManager
from pprint import pprint
import os
from dotenv import load_dotenv

if not os.environ.get("AZURE_STORAGE_ACCOUNT_NAME"):
    load_dotenv()
    if not os.environ.get("AZURE_STORAGE_ACCOUNT_NAME"):
        print("AZURE_STORAGE_ACCOUNT_NAME not set. Exiting.")
        exit(1)


credential = AzureNamedKeyCredential(
    os.environ.get("AZURE_STORAGE_ACCOUNT_NAME"),
    os.environ.get("AZURE_STORAGE_ACCOUNT_KEY"),
)

service_client = TableServiceClient(
    endpoint="https://csb10033fff9f716c2d.table.core.windows.net/",
    credential=credential,
)

table_name = "rooms"
table_client = service_client.get_table_client(table_name)  # create_table_if_not_exists

entities = table_client.query_entities("")
stored_rooms = {}
for entity in entities:
    print(f"Entity: {entity['name']}")
    stored_rooms[entity["name"]] = True
    # for key in entity.keys():
    #    print("Key: {}, Value: {}".format(key, entity[key]))

storage_manager = StorageManager()
rooms = storage_manager.get_rooms()
for room in rooms.values():
    room["PartitionKey"] = "corvid"
    room["RowKey"] = room["name"]


# my_entity = {
#    "PartitionKey": "test",
#    "RowKey": "room1",
#    "name": "room1",
#    "description": "room1 description",
#    "image": "room1.png",
# }
