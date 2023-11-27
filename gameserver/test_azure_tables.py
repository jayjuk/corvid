from azure.core.credentials import AzureNamedKeyCredential
from azure.data.tables import TableServiceClient, TableClient
import storagemanager
from pprint import pprint

credential = AzureNamedKeyCredential(
    "csb10033fff9f716c2d",
    "I7z/zXfGLCaiKhfJ9pMFLzOJBRnJVo3qOUc+J2IbYuYlkfjl2vU5el9nspdwzHND/6Iisq8vQp/8+ASt0DafXg==",
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


rooms = storagemanager.get_rooms()
for room in rooms.values():
    room["PartitionKey"] = "jaysgame"
    room["RowKey"] = room["name"]


# my_entity = {
#    "PartitionKey": "test",
#    "RowKey": "room1",
#    "name": "room1",
#    "description": "room1 description",
#    "image": "room1.png",
# }
