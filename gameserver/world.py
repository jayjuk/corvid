from logger import setup_logger, exit

# Set up logger
logger = setup_logger()

import aimanager
from storagemanager import StorageManager
from merchant import Merchant
from room import Room
from animal import Animal
from object import Object
from player import Player


class World:

    # Constructor
    def __init__(
        self,
        storage_manager,
        mode=None,
        ai_enabled=True,
        name="jaysgame",
        images_enabled=True,
    ):

        self.name = name
        self.storage_manager = storage_manager
        self.directions = {
            "north": (0, 1),
            "south": (0, -1),
            "east": (1, 0),
            "west": (-1, 0),
        }
        self.grid_references = {}
        self.room_objects = {}
        # Register of entities with name as key
        self.entities = {}
        self.done_path = {}

        # Populate dictionary of room objects, keyed off room name (aka location)
        self.rooms = self.load_rooms()

        # Only load objects and merchants if not in any special mode
        if not mode:
            self.load_entities()
            self.load_room_objects()

        # Separate AI manager for images (can use different model)
        if ai_enabled and images_enabled:
            # Image AI manager
            logger.info("Creating separate AI manager for image generation")
            self.image_ai_manager = aimanager.AIManager(
                system_message="You are helping to create an adventure game.",
                model_name="stable-diffusion-xl-1024-v1-0",  # stable-diffusion-v1-6 or gpt-3.5-turbo
            )
        else:
            logger.warning("AI and/or cloud image storage not enabled.")
            self.image_ai_manager = None

    # Get the objective of the game
    def get_objective(self):
        return (
            "The aim of this game is to earn enough money to buy The Button. "
            + "You don't know what will happen when you press The Button, but you know it will be good. "
            + "The first player to press the button (in their possession) wins the game! "
            + "Hint: earn money buy exploring the game world, finding items and selling them to a merchant."
        )

    def load_rooms(self):
        # Get rooms from storage
        rooms_list = self.storage_manager.get_game_objects(self.name, "Room")
        store_default_rooms = False
        if not rooms_list:
            logger.warning("No rooms found in cloud - loading from static")
            rooms_list = self.storage_manager.get_default_world_data(self.name, "rooms")
            store_default_rooms = True
        # Add room name to each room
        rooms_dict = {}
        for room in rooms_list:
            r = Room(world=self, init_dict=room)
            rooms_dict[r.name] = r
        # Set default room
        self.default_location = "Road"
        if self.default_location not in rooms_dict:
            # Default to alphabetically first room
            # TODO #76 Make starting room per world data / configurable
            self.default_location = list(sorted(rooms_dict.keys()))[0]

        # Add a grid reference for each room. This is used to validate that rooms don't overlap
        # Start with the first room found, grid references can go negative
        self.add_grid_references(
            rooms_dict, self.get_location(), rooms_dict[self.get_location()], 0, 0
        )
        if store_default_rooms:
            logger.info(f"Storing default rooms in database for new world {self.name}")
            self.storage_manager.store_game_objects(
                self.name, list(rooms_dict.values())
            )
        return rooms_dict

    def add_grid_references(
        self, rooms, room_name, room, x, y, prv_direction=None, indent=0
    ):
        grid_ref_str = f"{x},{y}"
        logger.debug(
            " " * indent + f"Checking grid reference {grid_ref_str} at {room_name}"
        )
        room.grid_reference = grid_ref_str
        if grid_ref_str in self.grid_references:
            if room_name not in self.grid_references[grid_ref_str]:
                logger.error(
                    f"{room_name} has the same grid reference as {self.grid_references[grid_ref_str]}"
                )
                self.grid_references[grid_ref_str].append(room_name)
        else:
            # logger.info(f"Adding grid reference {grid_ref_str} to {room_name}")
            self.grid_references[grid_ref_str] = [room_name]
        # Go through each exit and recursively add grid references
        for direction, next_room in room.exits.items():
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

    def get_location(self):
        return self.default_location

    def get_directions(self):
        return list(self.directions.keys())

    def generate_map(self, rooms, mode="grid"):
        # Generate a map of the world in text form
        if mode == "grid":
            world_map = ""
            # Get the min and max x and y
            min_x = 0
            max_x = 0
            min_y = 0
            max_y = 0
            for room in rooms:
                if not hasattr(rooms[room], "grid_reference"):
                    logger.error(f"No grid reference for {room}")
                else:
                    x = int(rooms[room].grid_reference.split(",")[0])
                    y = int(rooms[room].grid_reference.split(",")[1])
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
                    world_map += (
                        "&".join(self.grid_references.get(f"{x},{y}", [])) + "\t"
                    )
                world_map += "\n"
            return world_map
        else:
            world_map = ""
            for room in rooms:
                world_map += room + ": " + rooms[room].description + "\n"
                for exit in rooms[room].exits:
                    world_map += "  " + exit + ": " + rooms[room].exits[exit] + "\n"
            return world_map

    def get_exits(self, location):
        return list(self.rooms[location].exits.keys())

    def get_next_room(self, location, direction):
        return self.rooms[location].exits[direction]

    def get_room_exits_description(self, room):
        exits = " Available exits: "
        for exit in self.rooms[room].exits:
            exits += exit + ": " + self.rooms[room].exits[exit] + ".  "
        return exits

    def get_room_build_options(self, room):
        # Check that there is not already a room in this location based on the grid reference
        # Get the grid reference of the current room
        current_room_grid_reference = self.rooms[room].grid_reference

        build_directions = []
        for direction in self.directions:
            if direction not in self.rooms[room].exits:
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
        # TODO #77 Review logic around deciding when to show build options in room description
        description = ""
        if not brief:
            # Contents of curly brackets removed from AI description,
            # Actual brackets removed in UI
            description = "{" + self.rooms[room].description + "\n" + "}"

        if show_exits:
            description += self.get_room_exits_description(room)

        # Only show build options to builders
        if role == "builder":
            description += self.get_room_build_options(room)

        if show_objects:
            for object in self.room_objects.get(room, []):
                description += f" There is {object.get_name(article='a')} here."
        return description

    def get_room_image_url(self, room_name):
        url = self.storage_manager.get_image_url(self.name, self.rooms[room_name].image)
        logger.info(f"URL for {self.rooms[room_name].name}: {url}")
        return url

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
        current_location,
        direction,
        new_room_name,
        room_description,
        creator="system",
    ):
        # Check room name is not taken in any case (case insensitive)
        for room in self.rooms:
            if str(room).lower() == str(new_room_name).lower():
                return f"Sorry, there is already a room called '{new_room_name}'."

        # Check that the current room does not already have  an exit in the specified direction
        if direction in self.get_exits(current_location):
            return f"Sorry, there is already an exit in the {direction} from {current_location}."

        # Resolve pointer to current room object
        current_room = self.rooms[current_location]

        # Check that there is not already a room in this location based on the grid reference
        # Get the next x and y
        next_x = (
            int(current_room.grid_reference.split(",")[0])
            + self.directions[direction][0]
        )
        next_y = (
            int(current_room.grid_reference.split(",")[1])
            + self.directions[direction][1]
        )
        # Check if there is already a room in this location
        new_grid_reference = f"{next_x},{next_y}"
        if new_grid_reference in self.grid_references:
            return (
                f"Sorry, there is already a room to the {direction} of {current_location}, "
                + f"called {self.grid_references[f'{next_x},{next_y}']}. It must be accessed from somewhere else. "
                + self.get_room_build_options(current_room)
            )

        # Format the room name to be title case
        new_room_name = new_room_name.title()

        logger.info(
            f"Adding room {new_room_name} to the {direction} of {current_location}"
        )

        # Try to create the image and save it
        if self.image_ai_manager:
            try:
                image_name, image_data = self.image_ai_manager.create_image(
                    new_room_name, room_description
                )
                if image_data:
                    self.storage_manager.store_image(self.name, image_name, image_data)
                else:
                    logger.error(
                        "Error creating/saving image - returned no data, this room will be created without one"
                    )
            except Exception as e:
                logger.error(
                    f"Error creating/saving image ({e}), this room will be created without one"
                )
        else:
            logger.warning("Image generation not enabled.")

        # Add the new room to the exits of the current room
        current_room.exits[direction] = new_room_name
        #  TODO #86 Effect transactionality around storage of new room
        self.storage_manager.store_game_object(self.name, current_room)

        # Create and store room
        new_room_object = Room(
            self,
            new_room_name,
            room_description,
            exits={self.get_opposite_direction(direction): current_location},
            grid_reference=new_grid_reference,
            image=image_name,
            creator=creator,
        )
        self.storage_manager.store_game_object(self.name, new_room_object)
        self.rooms[new_room_name] = new_room_object

    # Search room for object by name and return reference to it if found
    def search_object(self, object_name, location):
        logger.info(f"Searching for object {object_name} in {location}")
        for object in self.room_objects.get(location, []):
            logger.info(f"  Checking {object.get_name()}")
            # Return the first object that includes the given object name
            # So "get clock" will find "dusty clock" and "grandfather clock"
            if object_name and (
                object_name
                and object_name.lower() in object.get_name().lower()
                or object_name.lower() == "all"
            ):
                return object
        return None

    # Room objects getter
    def get_room_objects(self, location):
        return self.room_objects.get(location, [])

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
    def load_room_objects(self):
        logger.info("Loading room objects...")
        object_load_count = 0
        for this_object in self.storage_manager.get_game_objects(self.name, "Object"):
            # Populate the room_object_map with object versions of the objects
            o = Object(world=self, init_dict=this_object)
            self.register_object(o)
            object_load_count += 1
        if not object_load_count:
            logger.info("No objects found, loading from file instead")
            self.load_default_objects()

    def load_default_objects(self):
        for object_data in self.storage_manager.get_default_world_data(
            self.name, "objects"
        ):
            logger.info(f"Loading and storing object {object_data['name']}")
            o = Object(world=self, init_dict=object_data)
            self.storage_manager.store_game_object("jaysgame", o)
            self.register_object(o)

    def register_object(self, object):
        # Is it a room or an entity?
        if object.location in self.entities:
            self.entities[object.location].inventory.append(object)
        else:
            if object.location not in self.rooms:
                # TODO #78 Improve robustness of object location on restart, possibly recording default / starting location per object in data and JSON
                logger.info(
                    f"Object location {object.location} for object {object.name} does not correspond to a room or entity. Resetting it to default location."
                )
                # This will also register the object with the room, and store the update
                object.set_room(self.default_location)
            else:
                # Add object to list of objects for its starting room
                self.add_object_to_room(object, object.location)

    def load_entities(self):
        if self.entities:
            exit("Load_entities called when entities are already registered!")
        logger.info("Loading entities...")
        for entity_role in ("Animal", "Merchant"):
            for this_object in self.storage_manager.get_game_objects(
                self.name, entity_role
            ):
                logger.info(f"Loading entity {this_object['name']}")
                # Populate the room_object_map with object versions of the objects
                # TODO #79 Streamline merchant and animal DB->object loading
                if this_object.get("role") == "merchant":
                    entity_object = Merchant(
                        self,
                        name=this_object["name"],
                        location=this_object["location"],
                        inventory=[],
                        description=this_object.get("description", ""),
                    )
                elif this_object.get("role") == "animal":
                    entity_object = Animal(
                        self,
                        name=this_object["name"],
                        location=this_object["location"],
                        description=this_object.get("description", ""),
                        actions=this_object.get("actions", []),
                        action_chance=this_object.get("action_chance", 0.5),
                    )
                self.register_entity(entity_object)
            if not self.entities:
                # Storage empties - load from file
                # TODO #80 Consider moving default data loading from file down from world to storage manager
                logger.info("No stored entities - loading from file instead")
                self.load_default_entities()

    def load_default_entities(self):
        logger.info("Loading default entities from file")
        for entity in self.storage_manager.get_default_world_data(
            self.name, "entities"
        ):
            logger.info(f"Loading {entity['name']}")
            if entity["type"] == "merchant":
                entity_object = Merchant(
                    self,
                    name=entity["name"],
                    location=entity["location"],
                    inventory=[],
                    description=entity.get("description", ""),
                )
            elif entity["type"] == "animal":
                entity_object = Animal(
                    self,
                    name=entity["name"],
                    location=entity["location"],
                    description=entity["description"],
                    actions=entity["actions"],
                    action_chance=entity["action_chance"],
                )
            else:
                exit(logger, f"Invalid or unsupported entity type {entity['type']}")
            self.storage_manager.store_game_object(self.name, entity_object)

    # Static method to register entity in the world
    def register_entity(self, entity):
        # TODO #81 Implement unique entity and object ID to allow ants coins etc
        self.entities[entity.name] = entity

    # Return list of entity names (e.g. for checking valid object starting locations)
    def get_entity_names(self):
        entity_names = []
        for entity in self.entities.values():
            entity_names.append(entity.name)
        return entity_names

    def get_currency(self, amount=None, short=False, plural=False):
        if amount is None:
            # Currency name alone
            if plural:
                return "pennies"
            return "penny"
        if short:
            return f"{amount}p"
        if amount == 1:
            return str(amount) + " penny"
        elif amount > 1 or amount == 0:
            return str(amount) + " pennies"

    def create_player(self, sid, name, role):
        # Access player's initial state if they have played before.
        stored_player_data = self.storage_manager.get_game_object(
            self.name, object_type="Player", rowkey_value=name
        )
        p = Player(self, sid, name, role, stored_player_data=stored_player_data)
        # Store player's data again (updates last login timestamp if nothing else)
        self.storage_manager.store_game_object(self.name, p)

        # TODO #82 Improve error handling around player creation
        return "", p
