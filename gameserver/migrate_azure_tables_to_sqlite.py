from storagemanager import StorageManager
from pprint import pprint
import os
from dotenv import load_dotenv
from pprint import pprint


def store_room_locally(conn, room):

    # Store new room and exits
    c = conn.cursor()
    c.execute(
        "INSERT INTO rooms VALUES (?,?,?)",
        (room["name"], room["description"], room["image"]),
    )
    exits_insert_sql = "INSERT INTO exits VALUES (?,?,?)"
    for direction in room["exits"]:
        c.execute(
            exits_insert_sql,
            (room["name"], direction, room["exits"][direction]),
        )

    c.close()

    conn.commit()


# Function to delete room locally
def delete_all_locally(conn):
    # Delete room and exits
    c = conn.cursor()
    c.execute("DELETE FROM exits")
    c.execute("DELETE FROM rooms")
    c.close()
    print("Deleted all data.")

    conn.commit()


def main():
    storage_manager = StorageManager()
    conn = storage_manager.get_local_db_connection()
    storage_manager.backup_local_db()
    storage_manager.create_sql_schema(conn)

    rooms = storage_manager.get_rooms_from_cloud()

    if not rooms:
        print("No rooms found on cloud! Exiting.")
        exit(1)

    delete_all_locally(conn)

    for room_name, room in rooms.items():
        print(room_name)
        store_room_locally(conn, room)

    conn.close()


if __name__ == "__main__":
    main()
