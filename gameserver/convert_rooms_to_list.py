from os import path
import json

full_path = path.join("world_data", "jaysgame", f"rooms.json")
with open(full_path, "r") as f:
    default_data = json.load(f)
r = []
for key, room in default_data.items():
    r.append(room)
with open(full_path + ".new", "w") as f:
    f.write(json.dumps(r))
