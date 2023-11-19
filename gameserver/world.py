import aimanager
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
    npcs = []
    done_path = {}
    starting_room = "Road"

    def __new__(cls, mode=None):
        if cls._instance is None:
            cls._instance = super(World, cls).__new__(cls)
            # Load rooms from storage
            cls._instance.rooms = cls._instance.load_rooms(mode)

            # Only load objects and merchants if not in any special mode
            if not mode:
                cls._instance.room_objects = cls._instance.load_room_objects(
                    cls._instance
                )
                cls._instance.load_merchants()

        return cls._instance

    def load_rooms(self, mode):
        # Get rooms from storage
        rooms = storagemanager.get_rooms()

        # Add a grid reference for each room. This is used to validate that rooms don't overlap
        # Start with the first room found, grid references can go negative
        self.add_grid_references(
            rooms, self.get_starting_room(), rooms[self.get_starting_room()], 0, 0
        )
        # Write map to file
        with open("rooms_dump.json", "w") as f:
            f.write(str(rooms))

        try:
            with open("map.csv", "w") as f:
                f.write(self.generate_map(rooms))
        except Exception as e:
            logger.error(f"Error writing map: {e}")
        return rooms

    def add_grid_references(
        self, rooms, room_name, room, x, y, prv_direction=None, indent=0
    ):
        grid_ref_str = f"{x},{y}"
        logger.info(
            " " * indent + f"Checking grid reference {grid_ref_str} at {room_name}"
        )
        room["grid_reference"] = grid_ref_str
        if grid_ref_str in self.grid_references:
            if room_name not in self.grid_references[grid_ref_str]:
                logger.info(
                    f"ERROR: {room_name} has the same grid reference as {self.grid_references[grid_ref_str]}"
                )
                self.grid_references[grid_ref_str].append(room_name)
        else:
            # logger.info(f"Adding grid reference {grid_ref_str} to {room_name}")
            self.grid_references[grid_ref_str] = [room_name]
        # Go through each exit and recursively add grid references
        for direction, next_room in room["exits"].items():
            # Get the next x and y
            next_x = x + self.directions[direction][0]
            next_y = y + self.directions[direction][1]
            # Add the grid reference to the next room and recursively add grid references
            # Keep track of each step taken so that we don't go back on ourselves
            key = room_name + " " + direction
            if not (
                key in self.done_path
                or (
                    prv_direction
                    and direction == self.get_opposite_direction(prv_direction)
                )
            ):
                self.done_path[key] = True
                self.add_grid_references(
                    rooms,
                    next_room,
                    rooms[next_room],
                    next_x,
                    next_y,
                    direction,
                    indent + 1,
                )

    def get_rooms(self):
        return self.rooms

    def get_starting_room(self):
        return self.starting_room

    def generate_map(self, rooms, mode="grid"):
        # Generate a map of the world in text form
        if mode == "grid":
            map = ""
            # Get the min and max x and y
            min_x = 0
            max_x = 0
            min_y = 0
            max_y = 0
            for room in rooms:
                print(room)
                if "grid_reference" not in rooms[room]:
                    print("ERROR: no grid reference for", room)
                else:
                    x = int(rooms[room]["grid_reference"].split(",")[0])
                    y = int(rooms[room]["grid_reference"].split(",")[1])
                    if x < min_x:
                        min_x = x
                    if x > max_x:
                        max_x = x
                    if y < min_y:
                        min_y = y
                    if y > max_y:
                        max_y = y
            # Generate the map
            for y in range(max_y, min_y - 1, -1):
                for x in range(min_x, max_x + 1):
                    map += "&".join(self.grid_references.get(f"{x},{y}", [])) + "\t"
                map += "\n"
            return map
        else:
            map = ""
            for room in rooms:
                map += room + ": " + rooms[room]["description"] + "\n"
                for exit in rooms[room]["exits"]:
                    map += "  " + exit + ": " + rooms[room]["exits"][exit] + "\n"
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

    def get_room_description(
        self, room, brief=False, role=None, show_objects=True, show_exits=True
    ):
        # TODO: decide when to show build options
        description = ""
        if not brief:
            description = self.rooms[room]["description"] + "\n"

        if show_exits:
            description += self.get_room_exits(room)

        # Only show build options to builders
        if role == "builder":
            description += self.get_room_build_options(room)

        if show_objects:
            for object in self.room_objects.get(room, []):
                description += f" There is {object.get_name(article='a')} here."
        return description

    def get_opposite_direction(self, direction):
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

        logger.info(f"Adding room {new_room_name} to the {direction} of {current_room}")

        self.rooms[new_room_name] = {}
        self.rooms[new_room_name]["grid_reference"] = new_grid_reference
        self.rooms[new_room_name]["description"] = room_description
        self.rooms[new_room_name]["exits"] = {}
        self.rooms[new_room_name]["image"] = aimanager.create_image(
            new_room_name, room_description
        )
        # Add the new room to the exits of the current room
        self.rooms[current_room]["exits"][direction] = new_room_name
        # Add the current room to the exits of the new room
        self.rooms[new_room_name]["exits"][
            self.get_opposite_direction(direction)
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
        apple = Object(self, "Apple", "A juicy apple.", price=1)
        banana = Object(self, "Banana", "A yellowy banana.", price=2)
        pear = Object(self, "Pear", "A peary pear.", price=3)
        gambinos_stuff = [apple, banana, pear]
        Merchant(self, "Gambino", "Road", gambinos_stuff)
        # TODO: more stuff with merchant

    # Static method to register NPC in the world
    def register_npc(self, npc):
        self.npcs.append(npc)
