import imagemanager
import storagemanager
from gameutils import log


class World:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(World, cls).__new__(cls)
            # Load rooms from storage
            cls._instance.rooms = cls._instance.load_rooms()
            cls._instance.directions = {
                "north": (0, 1),
                "south": (0, -1),
                "east": (1, 0),
                "west": (-1, 0),
            }

        return cls._instance

    def load_rooms(self):
        rooms = storagemanager.get_rooms()
        if not rooms:
            rooms = storagemanager.get_default_rooms()
        # Add a grid reference for each room. This is used to validate that rooms don't overlap
        # Start with the first room found, grid references can go negative
        first_room_name = list(rooms.keys())[0]
        self.add_grid_references(rooms, first_room_name, rooms[first_room_name], 0, 0)
        return rooms

    def add_grid_references(self, rooms, room_name, room, x, y):
        room["grid_reference"] = f"{x},{y}"
        log(f"Adding grid reference {room['grid_reference']} to {room_name}")
        # Go through each exit and recursively add grid references
        for direction, next_room in room["exits"].items():
            if "grid_reference" in rooms[next_room]:
                # This room has already been visited, so skip it
                continue
            # Get the next x and y
            next_x = x + self.directions[direction][0]
            next_y = y + self.directions[direction][1]
            # Add the grid reference to the next room and recursively add grid references
            self.add_grid_references(rooms, next_room, rooms[next_room], next_x, next_y)

    def get_rooms(self):
        return self.rooms

    def get_text_map(self):
        # Generate a map of the world in text form
        map = ""
        for room in self.rooms:
            map += room + ": " + self.rooms[room]["description"] + "\n"
            for exit in self.rooms[room]["exits"]:
                map += "  " + exit + ": " + self.rooms[room]["exits"][exit] + "\n"
        return map

    def get_room_exits(self, room):
        exits = " Available exits: "
        for exit in self.rooms[room]["exits"]:
            exits += exit + ": " + self.rooms[room]["exits"][exit] + ".  "
        return exits

    def get_room_description(self, room, brief=False):
        if brief:
            description = ""
        else:
            description = self.rooms[room]["description"]
        # Always describe exits
        description += self.get_room_exits(room)
        return description

    def opposite_direction(self, direction):
        directions = {
            "north": "south",
            "south": "north",
            "east": "west",
            "west": "east",
        }
        return directions.get(direction, None)

    def add_room(
        self,
        current_room,
        direction,
        new_room_name,
        room_description,
        creator_name=None,
    ):
        # Check room name is not taken in any case (case insensitive)
        for room in self.rooms:
            if str(room).lower() == str(new_room_name).lower():
                return f"Sorry, there is already a room called '{new_room_name}'."

        self.rooms[new_room_name] = {}
        self.rooms[new_room_name]["description"] = room_description
        self.rooms[new_room_name]["exits"] = {}
        self.rooms[new_room_name]["image"] = imagemanager.create_image(
            new_room_name, room_description
        )
        # Add the new room to the exits of the current room
        self.rooms[current_room]["exits"][direction] = new_room_name
        # Add the current room to the exits of the new room
        self.rooms[new_room_name]["exits"][
            self.opposite_direction(direction)
        ] = current_room
        # Store current and new room (current has changed in that exit has been added)
        storagemanager.store_rooms(
            self.rooms, self.rooms[new_room_name], current_room, direction
        )
