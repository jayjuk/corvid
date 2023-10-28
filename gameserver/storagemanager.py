import os
import sqlite3
import json
from gameutils import create_folder_if_not_exists, log


# For now stateless as storage is infrequent
def get_connection():
    return sqlite3.connect("gameserver.db")


def create_schema():
    conn = get_connection()
    c = conn.cursor()
    # Check if schema exists, if not create it
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
    conn.commit()
    conn.close()


# Store the rooms from the dict format in the database
def store_rooms(rooms, new_room, changed_room, new_exit_direction):
    log(
        f"Storing new room {new_room['name']} and adding exit {new_exit_direction} to {changed_room}"
    )
    # Check if schema exists, if not create it
    create_schema()
    conn = get_connection()
    c = conn.cursor()

    # Store new room and exits
    c.execute(
        "INSERT INTO rooms VALUES (?,?,?)",
        (new_room["name"], new_room["description"], new_room["image"]),
    )
    for direction in new_room["exits"]:
        c.execute(
            "INSERT INTO exits VALUES (?,?,?)",
            (new_room["name"], direction, new_room["exits"][direction]),
        )

    # Store only the new exit of new room and exits
    c.execute(
        "INSERT INTO exits VALUES (?,?,?)",
        (changed_room, new_exit_direction, new_room["name"]),
    )

    conn.commit()
    conn.close()

    # Check subfolder exists for saving user generated maps
    # TODO: for now this is saving every version, and this is really just a temporary backup
    user_map_folder_path = "user_maps"
    create_folder_if_not_exists(user_map_folder_path)
    with open(
        user_map_folder_path + os.sep + ".user_generated_map_backup.tmp",
        "w",
    ) as f:
        json.dump(rooms, f, indent=4)


# Check if the schema exists but don't create if not
# Handle that the connection may not exist
def check_schema():
    conn = get_connection()
    if not conn:
        return False
    c = conn.cursor()
    # Check if schema exists, if not create it
    c.execute("""SELECT name FROM sqlite_master WHERE type='table' AND name='rooms'""")
    schema_exists = c.fetchone()
    conn.close()
    return schema_exists


# Get rooms and return in the dict format expected by the game server
def get_rooms():
    conn = get_connection()
    # Check schema
    if conn is None or not check_schema():
        return get_default_rooms()
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
    return rooms_dict


def get_default_rooms():
    # This is the built-in static rooms file
    default_map_file = "map.json"
    with open(default_map_file, "r") as f:
        rooms = json.load(f)
    return rooms
