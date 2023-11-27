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


def get_rowkeys_dict_from_table_client(table_client):
    entities = table_client.query_entities("")
    rowkeys = {}
    for entity in entities:
        rowkeys[entity["RowKey"]] = True
    return rowkeys


rooms_client = service_client.create_table_if_not_exists("rooms")
stored_rooms = get_rowkeys_dict_from_table_client(rooms_client)

exits_client = service_client.create_table_if_not_exists("exits")
stored_exits = get_rowkeys_dict_from_table_client(exits_client)

rooms = storagemanager.get_rooms()
for room in rooms.values():
    # print(room)
    room["PartitionKey"] = "jaysgame"
    room["RowKey"] = room["name"]

    # Store room in Azure
    if room["name"] not in stored_rooms:
        print(f"Storing {room['name']}")
        room_only = room.copy()
        del room_only["exits"]
        rooms_client.create_entity(entity=room_only)
    else:
        print(f"Room {room['name']} already stored")

    # Store exits in Azure
    for direction, destination in room["exits"].items():
        exit_dict = {
            "PartitionKey": "jaysgame",
            "RowKey": f"{room['name']}_{direction}",
            "room": room["name"],
            "direction": direction,
            "destination": destination,
        }
        if exit_dict["RowKey"] not in stored_exits:
            print(f"Storing {exit_dict['RowKey']}")
            exits_client.create_entity(entity=exit_dict)
        else:
            print(f"Exit {exit_dict['RowKey']} already stored")
