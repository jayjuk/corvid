import json
from os import path

with open(path.join("world_data", "starting_objects.json"), "r") as f:
    for item_name, object_description, price, starting_room in json.load(f):
        o = {
            "name": item_name,
            "description": object_description,
            "price": price,
            "starting_room": starting_room,
        }
        print(json.dumps(o) + ",")
