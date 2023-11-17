import imagemanager
import storagemanager
from logger import setup_logger
from merchant import Merchant
from object import Object

# Set up logging
logger = setup_logger()


class World:
    _instance = None
    directions = {
        "north": (0, 1),
        "south": (0, -1),
        "east": (1, 0),
        "west": (-1, 0),
    }
    grid_references = {}
    room_objects = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(World, cls).__new__(cls)
            # Load rooms from storage
            cls._instance.rooms = cls._instance.load_rooms()
            # Load objects and their positions
            cls._instance.room_objects = cls._instance.load_room_objects(cls._instance)

            cls._instance.load_merchants()

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
        logger.info(f"Adding grid reference {x},{y} to {room_name}")
        room["grid_reference"] = f"{x},{y}"
        if f"{x},{y}" in self.grid_references:
            logger.info(
                f"ERROR: {room_name} has the same grid reference as {self.grid_references[f'{x},{y}']}"
            )
            exit()
        self.grid_references[f"{x},{y}"] = room_name
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

    def get_starting_room(self):
        return "Road"

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

    def get_room_build_options(self, room):
        # Check that there is not already a room in this location based on the grid reference
        # Get the grid reference of the current room
        current_room_grid_reference = self.rooms[room]["grid_reference"]

        build_directions = []
        for direction in self.directions:
            if direction not in self.rooms[room]["exits"]:
                # Get the hypothetical x and y of this direction
                x = (
                    int(current_room_grid_reference.split(",")[0])
                    + self.directions[direction][0]
                )
                y = (
                    int(current_room_grid_reference.split(",")[1])
                    + self.directions[direction][1]
                )
                # Check if there is already a room in this location
                if f"{x},{y}" not in self.grid_references:
                    build_directions.append(direction)

        if build_directions:
            return (
                "Available directions in which you can build: "
                + ", ".join(build_directions)
                + "."
            )
        else:
            return "You cannot build from here."

    def get_room_description(self, room, brief=False):
        # TODO: decide when to show build options
        if brief:
            description = self.get_room_exits(room) + self.get_room_build_options(room)
        else:
            description = (
                self.rooms[room]["description"]
                + self.get_room_exits(room)
                + self.get_room_build_options(room)
            )
        for object in self.room_objects.get(room, []):
            description += f" There is {object.get_name(article='a')} here."
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

        # Check that the current room does not already have  an exit in the specified direction
        if direction in self.rooms[current_room]["exits"]:
            return f"Sorry, there is already an exit in the {direction} from {current_room}."

        # Check that there is not already a room in this location based on the grid reference
        # Get the grid reference of the current room
        current_room_grid_reference = self.rooms[current_room]["grid_reference"]
        # Get the next x and y
        next_x = (
            int(current_room_grid_reference.split(",")[0])
            + self.directions[direction][0]
        )
        next_y = (
            int(current_room_grid_reference.split(",")[1])
            + self.directions[direction][1]
        )
        # Check if there is already a room in this location
        new_grid_reference = f"{next_x},{next_y}"
        if new_grid_reference in self.grid_references:
            return (
                f"Sorry, there is already a room to the {direction} of {current_room}, "
                + f"called {self.grid_references[f'{next_x},{next_y}']}. It must be accessed from somewhere else. "
                + self.get_room_build_options(current_room)
            )

        # Format the room name to be title case
        new_room_name = new_room_name.title()

        self.rooms[new_room_name] = {}
        self.rooms[new_room_name]["grid_reference"] = new_grid_reference
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
            self.rooms,
            new_room_name,
            current_room,
            direction,
        )

    # Search room for object by name and return reference to it if found
    def search_object(self, object_name, room):
        logger.info(f"Searching for object {object_name} in {room}")
        for object in self.room_objects.get(room, []):
            logger.info(f"  Checking {object.get_name()}")
            if object.get_name().lower() == object_name.lower():
                return object
        return None

    # Room objects getter
    def get_room_objects(self, room):
        return self.room_objects.get(room, [])

    # Room objects setter
    def add_object_to_room(self, object, room_name):
        if room_name in self.room_objects:
            self.room_objects[room_name].append(object)
        else:
            self.room_objects[room_name] = [object]

    # Room objects setter
    def remove_object_from_room(self, object, room_name):
        if room_name in self.room_objects:
            for i, o in enumerate(self.room_objects[room_name]):
                if o.name == object.name:
                    self.room_objects[room_name].pop(i)
                    return

    # Load objects and return a map of room to objects
    def load_room_objects(self, world):
        # TODO: Store and reload object state
        # Stubbed test data for now
        test_object_data = [
            ["Thingy", "This is a thingy", "Road"],
            ["Zingy", "This is a zingy", "North Road"],
            ["Dingy", "This is a dingy", "Norther Road"],
        ]
        room_object_map = {}
        for _ in test_object_data:
            (object_name, object_description, starting_room) = _
            # Populate the room_object_map with object versions of the objects!
            o = Object(world, object_name, object_description, starting_room)
            if starting_room in room_object_map:
                room_object_map[starting_room].append(o)
            else:
                room_object_map[starting_room] = [o]

        return room_object_map

    def load_merchants(self):
        # Merchant objects have no room
        apple = Object("Apple", "A juicy apple.", None, 1)
        banana = Object("Banana", "A yellowy banana.", None, 2)
        pear = Object("Pear", "A peary pear.", None, 3)
        gambinos_stuff = [apple, banana, pear]
        gambino = Merchant(self, "Gambino", "Road", gambinos_stuff)
        # TODO: more stuff with merchant
