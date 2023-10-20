import sqlite3


# For now stateless as storage is infrequent
def get_connection():
    return sqlite3.connect("gameserver.db")


def create_schema():
    conn = get_connection()
    c = conn.cursor()
    # Check if schema exists, if not create it
    c.execute(
        """CREATE TABLE IF NOT EXISTS locations
                 (name text, description text, image text)"""
    )
    # Create index on name
    c.execute("CREATE INDEX IF NOT EXISTS location_name ON locations (name)")

    # Create child of locations table to store the exits per location
    c.execute(
        """CREATE TABLE IF NOT EXISTS exits
                 (location text, direction text, destination text)"""
    )
    conn.commit()
    conn.close()


# Store the locations from the dict format in the database
def store_locations(locations):
    # Check if schema exists, if not create it
    create_schema()
    conn = get_connection()
    c = conn.cursor()
    # Get existing location names and only store new ones (currently no updates)
    c.execute("SELECT name FROM locations")
    existing_locations = c.fetchall()
    existing_location_names = [location[0] for location in existing_locations]
    for location in locations:
        if location["name"] in existing_location_names:
            continue
        # Store location and exists
        c.execute(
            "INSERT INTO locations VALUES (?,?,?)",
            (location["name"], location["description"], location["image"]),
        )
        for direction in location["exits"]:
            c.execute(
                "INSERT INTO exits VALUES (?,?,?)",
                (location["name"], direction, location["exits"][direction]),
            )
    conn.commit()
    conn.close()


# Check if the schema exists but don't create if not
# Handle that the connection may not exist
def check_schema():
    conn = get_connection()
    if not conn:
        return False
    c = conn.cursor()
    # Check if schema exists, if not create it
    c.execute(
        """SELECT name FROM sqlite_master WHERE type='table' AND name='locations'"""
    )
    schema_exists = c.fetchone()
    conn.close()
    return schema_exists


# Get locations and return in the dict format expected by the game server
def get_locations():
    conn = get_connection()
    if conn is None:
        return {}
    # Check schema
    if not check_schema():
        return {}
    # Get locations and exits
    c = conn.cursor()
    c.execute("SELECT * FROM locations")
    locations = c.fetchall()
    c.execute("SELECT * FROM exits")
    exits = c.fetchall()
    # Convert to dict
    locations_dict = {}
    for location in locations:
        locations_dict[location[0]] = {
            "name": location[0],
            "description": location[1],
            "image": location[2],
            "exits": {},
        }
    for exit in exits:
        locations_dict[exit[0]]["exits"][exit[1]] = exit[2]
    conn.close()
    return locations_dict
