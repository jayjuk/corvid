from logger import setup_logger, exit

# Set up logger before all other imports
logger = setup_logger()

from typing import Dict, Optional, Tuple, Any, List
from aimanager import AIManager
from merchant import Merchant
from room import Room
from animal import Animal
from gameitem import GameItem
from player import Player
from entity import Entity
from gameitem import GameItem
from typing import List, Dict, Union, Optional


class World:

    # Constructor
    def __init__(
        self,
        name: str,
        storage_manager: Any,
        mode: Optional[str] = None,
        ai_manager: AIManager = None,
    ) -> None:

        logger.info(f"Creating world {name}")

        # Flag to indicate if the world is empty
        # Only set to true if we load from empty.json
        self.is_empty: bool = False

        self.name: str = name
        self.ai_manager: AIManager = ai_manager
        self.storage_manager: Any = storage_manager
        self.directions: Dict[str, Tuple[int, int, str]] = {
            "north": (0, 1, "south"),
            "south": (0, -1, "north"),
            "east": (1, 0, "west"),
            "west": (-1, 0, "east"),
        }
        self.grid_references: Dict = {}
        self.room_items: Dict = {}
        # Register of entities with name as key
        self.entities: Dict[str, Entity] = {}
        self.done_path: Dict[str, bool] = {}

        # Populate dictionary of room items, keyed off room name (aka location)
        self.rooms: Dict = self.load_rooms()

        # Only load items and merchants if not in any special mode
        if not mode:
            self.load_entities()
            self.load_room_items()

    # Get the objective of the game
    def get_objective(self, player: Optional[Player] = None) -> str:
        if player and player.role == "builder":
            return "You are a builder and your objective is to create a wonderful game world."
        return (
            "The aim of this game is to earn enough money to buy The Button. "
            + "You don't know what will happen when you press The Button, but you know it will be good. "
            + "The first player to press the button (in their possession) wins the game! "
            + "Hint: earn money buy exploring the game world, finding items and selling them to a merchant."
        )

    def load_rooms(self) -> Dict[str, Room]:

        logger.info("Loading rooms...")

        # Get rooms from storage
        rooms_list: List[Dict[str, Any]] = self.storage_manager.get_game_objects(
            self.name, "Room"
        )
        store_default_rooms = False
        if not rooms_list:
            logger.warning("No rooms found in cloud - loading from static")
            rooms_list = self.storage_manager.get_default_world_data(self.name, "rooms")
            store_default_rooms = True
        if len(rooms_list) == 0:
            exit(logger, "No rooms found in cloud or static data")
        if len(rooms_list) == 1 and rooms_list[0]["name"] == "The Void":
            self.is_empty = True

        # Add room name to each room
        rooms_dict: Dict[str, Room] = {}
        for room in rooms_list:
            r = Room(world=self, init_dict=room)
            rooms_dict[r.name] = r

        # Set default room
        self.default_location: str = "Road"
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
        self,
        rooms: Dict[str, Room],
        room_name: str,
        room: Room,
        x: int,
        y: int,
        prv_direction: str = None,
        indent: int = 0,
    ) -> None:
        grid_ref_str: str = f"{x},{y}"
        logger.debug(
            " " * indent + f"Checking grid reference {grid_ref_str} at {room_name}"
        )
        room.grid_reference: str = grid_ref_str
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
            next_x: int = x + self.directions[direction][0]
            next_y: int = y + self.directions[direction][1]
            # Add the grid reference to the next room and recursively add grid references
            # Keep track of each step taken so that we don't go back on ourselves
            key: str = room_name + " " + direction
            if not (
                key in self.done_path
                or (
                    prv_direction
                    and direction == self.get_opposite_direction(prv_direction)
                )
            ):
                self.done_path[key] = True
                if next_room not in rooms:
                    exit(
                        logger,
                        f"Next room {next_room} not found in rooms but referenced by {room_name}",
                    )
                self.add_grid_references(
                    rooms,
                    next_room,
                    rooms[next_room],
                    next_x,
                    next_y,
                    direction,
                    indent + 1,
                )

    def get_rooms(self) -> Dict[str, Room]:
        return self.rooms

    def get_rooms_missing_images(self) -> List[str]:
        rooms_missing_images: List[Tuple[str, str]] = []
        for room in self.rooms:
            if not hasattr(self.rooms[room], "image") or not self.rooms[room].image:
                rooms_missing_images.append(
                    [self.rooms[room].name, self.rooms[room].description]
                )
        return rooms_missing_images

    def get_location(self) -> str:
        return self.default_location

    def get_directions(self) -> List[str]:
        return list(self.directions.keys())

    def generate_map(self, rooms, mode="grid") -> str:
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

    def get_exits(self, location: str) -> List[str]:
        return list(self.rooms[location].exits.keys())

    def get_next_room(self, location: str, direction: str) -> str:
        return self.rooms[location].exits[direction]

    def get_room_exits_description(self, room: str) -> str:
        exits: str = " "
        for exit in self.rooms[room].exits:
            if exits == " ":
                exits += "Available exits: "
            exits += exit + ": " + self.rooms[room].exits[exit] + "; "
        # Replace last semicolon with a full stop
        if exits != " ":
            exits = exits[:-2] + "."
        return exits

    def get_room_build_options(self, location_name: str) -> str:
        # Check that there is not already a room in this location based on the grid reference
        # Get the grid reference of the current room
        current_room_grid_reference: str = self.rooms[location_name].grid_reference

        build_directions: List[str] = []
        for direction in self.directions:
            if direction not in self.rooms[location_name].exits:
                # Get the hypothetical x and y of this direction
                x: int = (
                    int(current_room_grid_reference.split(",")[0])
                    + self.directions[direction][0]
                )
                y: int = (
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
        self,
        room: str,
        brief: bool = False,
        role: Optional[str] = None,
        show_items: bool = True,
        show_exits: bool = True,
    ) -> str:
        # TODO #77 Review logic around deciding when to show build options in room description
        description: str = ""
        if not brief:
            # Contents of curly brackets removed from AI description,
            # Actual brackets removed in UI
            description = "{" + self.rooms[room].description + "\n" + "}"

        if show_exits:
            description += self.get_room_exits_description(room)

        # Only show build options to builders
        if role == "builder":
            description += " " + self.get_room_build_options(room)

        if show_items:
            description += self.get_room_items_description(room)
        return description

    def get_room_items_description(self, room: str, detail: bool = False) -> str:
        description: str = ""
        for item in self.room_items.get(room, []):
            description += f" There is {item.get_name(article='a')} here."
            if detail:
                description = description[:-1] + f": {item.description}"
        return description

    def get_room_image_url(self, room_name: str) -> str:
        url: str = self.storage_manager.get_image_url(
            self.name, self.rooms[room_name].image
        )
        logger.info(f"URL for {self.rooms[room_name].name}: {url}")
        return url

    def get_opposite_direction(self, direction: str) -> Optional[str]:
        # Return the opposite direction
        return self.directions[direction][2]

    def check_room_request(
        self,
        player: Player,
        direction: str,
        room_name: str,
        room_description: str,
    ) -> Tuple[str, str, str]:
        current_location: str = player.get_current_location()
        # Check room name is not taken in any case (case insensitive)
        for room in self.rooms:
            if str(room).lower() == str(room_name).lower():
                return f"Sorry, there is already a room called '{room_name}'.", "", ""

        # Check that the current room does not already have  an exit in the specified direction
        if direction in self.get_exits(current_location):
            return (
                f"Sorry, there is already an exit in the {direction} from {current_location}.",
                "",
                "",
            )

        # Resolve pointer to current room item
        current_room: Room = self.rooms[current_location]

        # Check that there is not already a room in this location based on the grid reference
        # Get the next x and y
        next_x: int = (
            int(current_room.grid_reference.split(",")[0])
            + self.directions[direction][0]
        )
        next_y: int = (
            int(current_room.grid_reference.split(",")[1])
            + self.directions[direction][1]
        )
        # Check if there is already a room in this location
        new_grid_reference: str = f"{next_x},{next_y}"
        if new_grid_reference in self.grid_references:
            return (
                (
                    f"Sorry, there is already a room to the {direction} of {current_location}, "
                    + f"called {self.grid_references[f'{next_x},{next_y}']}. It must be accessed from somewhere else. "
                    + self.get_room_build_options(current_location)
                ),
                "",
                "",
            )

        logger.info(f"Adding room {room_name} to the {direction} of {current_location}")

        # If player does not provide a room description, try to get one from the AI
        # TODO #93 Consider whether AI usage belongs inside World class
        if len(room_description) < 50:
            if self.ai_manager:
                prompt = self.generate_room_description_prompt(
                    room_name, room_description
                )
                return "", prompt, new_grid_reference
            else:
                return (
                    "Invalid input: room description missing and AI is not enabled.",
                    "",
                    "",
                )
        return "", "", new_grid_reference

    def generate_room_description_prompt(self, room_name: str, room_description: str):
        # Get existing room descriptions into a list for inspiration
        existing_room_descriptions: List[str] = [
            self.rooms[room].description for room in self.rooms.keys()
        ]

        prompt: str = (
            f"Generate an appropriate 30-50 word description for a new location in my adventure game world called '{self.name}'."
        )
        if len(existing_room_descriptions) > 1:
            prompt += " Pre-existing descriptions for inspiration:\n" + "\n,\n".join(
                existing_room_descriptions[0:10]
            )
        else:
            prompt += (
                " Here is an example of a room description:\n"
                + "A rickety wooden shed stands precariously, its peeling paint hinting at long-forgotten secrets. Its interior is a labyrinth of shadows, filled with the musty scent of damp earth and forgotten tools.\n"
                + "(This just gives you an idea of format and length, feel free to vary the style and theme, perhaps drawing inspiration from classic text adventure games of old...)."
            )
        prompt += f"\nThis room is called '{room_name}', the description should be appropriate to that.\n"

        if room_description:
            prompt += (
                f"Some inspiration for the room description:\n{room_description}\n"
            )
            prompt += "Respond with only a description of similar length to the examples above, nothing else.\n"
        return prompt  # Success

    def add_room(
        self,
        player: Player,
        current_location: str,
        direction: str,
        room_name: str,
        room_description: str,
        new_grid_reference: str,
    ) -> str:

        # Create and store room
        new_room: Room = Room(
            self,
            room_name,
            room_description,
            exits={self.get_opposite_direction(direction): current_location},
            grid_reference=new_grid_reference,
            image=None,
            creator=player.name or "system",
        )
        self.storage_manager.store_game_object(self.name, new_room)
        self.rooms[room_name] = new_room

        # Add the new room to the exits of the current room
        if current_location in self.rooms:
            self.rooms[current_location].exits[direction] = room_name
            #  TODO #86 Effect transactionality around storage of new room
            self.storage_manager.store_game_object(
                self.name, self.rooms[current_location]
            )
        return f"New location created: {room_description}"

    def update_room_image(self, room_name: str, image_name: str) -> None:
        self.rooms[room_name].image = image_name
        self.storage_manager.store_game_object(self.name, self.rooms[room_name])

    def update_room_description(self, room_name: str, description: str) -> None:
        self.rooms[room_name].description = description
        self.storage_manager.store_game_object(self.name, self.rooms[room_name])

    def delete_room(self, room_name: str) -> str:
        logger.info(f"Deleting room {room_name}")
        # Remove the room from the exits of all other rooms
        rooms_to_update = []
        for room in self.rooms:
            if room_name in self.rooms[room].exits.values():
                rooms_to_update.append(room)

        for room in rooms_to_update:
            for direction in list(self.rooms[room].exits.keys()):
                if self.rooms[room].exits[direction] == room_name:
                    del self.rooms[room].exits[direction]
                    self.storage_manager.store_game_object(self.name, self.rooms[room])
        # Delete the room
        del self.grid_references[self.rooms[room_name].grid_reference]
        del self.rooms[room_name]
        # Change default room
        if self.default_location == room_name:
            self.default_location = list(self.rooms.keys())[0]

        self.storage_manager.delete_game_object(
            self.name, "Room", room_name, location=""
        )
        logger.info(f"Room {room_name} has been deleted.")
        return f"Room {room_name} has been deleted."

    # Search room for item by name and return reference to it if found
    def search_item(self, item_name: str, location: str) -> Optional[GameItem]:
        for item in self.room_items.get(location, []):
            # Return the first item that includes the given item name
            # So "get clock" will find "dusty clock" and "grandfather clock"
            if item_name and (
                item_name.lower() in item.get_name().lower()
                or item_name.lower() == "all"
            ):
                return item
        return None

    # Room items getter
    def get_room_items(self, location: str) -> List[GameItem]:
        return self.room_items.get(location, [])

    # Room items setter
    def add_item_to_room(self, item: GameItem, room_name: str) -> None:
        if room_name in self.room_items:
            self.room_items[room_name].append(item)
        else:
            self.room_items[room_name] = [item]

    # Room items setter
    def remove_item_from_room(self, game_item: GameItem, room_name: str) -> None:
        if room_name in self.room_items:
            for i, o in enumerate(self.room_items[room_name]):
                if o.name == game_item.name:
                    self.room_items[room_name].pop(i)
                    return
            # If item not found in room, log error
            logger.error(f"Item {game_item.name} not found in room {room_name}")
        else:
            logger.error(f"Room {room_name} not found in room items map")

    # Load items and return a map of room to items
    def load_room_items(self) -> None:
        logger.info("Loading room items...")
        item_load_count: int = 0
        for this_item in self.storage_manager.get_game_objects(self.name, "GameItem"):
            # Populate the room_item_map with item versions of the items
            o: GameItem = GameItem(world=self, init_dict=this_item)
            self.register_item(o)
            item_load_count += 1
        if not item_load_count:
            logger.info("No items found, loading from file instead")
            self.load_default_items()

    def load_default_items(self) -> None:
        item_datas = self.storage_manager.get_default_world_data(self.name, "items")
        for item_data in item_datas:
            logger.info(f"Loading and storing item {item_data['name']}")
            o: GameItem = GameItem(world=self, init_dict=item_data)
            self.register_item(o)
            self.storage_manager.store_game_object(self.name, o)

    def create_item(self, name: str, description: str, location: str) -> Optional[str]:
        for reserved_word in (" from ", " up ", " to "):
            if reserved_word in name.lower():
                return f"Problems will arise if an item is created that contains '{reserved_word}'."

        # Format the item name to be title case
        name = name.title()

        logger.info(f"Creating item {name} in {location}")

        # Create and store item
        o: GameItem = GameItem(
            world=self, name=name, description=description, location=location
        )
        self.register_item(o)
        self.storage_manager.store_game_object(self.name, o)

    # Currently, must specify player to delete item, which is either in their possession or in their location
    def delete_item(self, item_name: str, player: Player) -> None:
        location: str
        if item_name in player.get_inventory():
            location = player.name
        else:
            location = player.get_current_location()

        item_to_delete: Optional[GameItem] = self.search_item(item_name, location)
        if item_to_delete:
            # Check if item is in room or an entity's possession
            if item_to_delete.location in self.entities:
                self.entities[location].inventory.remove(item_to_delete)
            else:
                self.remove_item_from_room(item_to_delete, location)
            self.storage_manager.delete_game_object(
                self.name, "GameItem", item_to_delete.name, location
            )

    def register_item(self, item: GameItem) -> None:
        # Is it a room or an entity?
        if item.location in self.entities:
            self.entities[item.location].inventory.append(item)
        else:
            if item.location not in self.rooms:
                # TODO #78 Improve robustness of item location on restart, possibly recording default / starting location per item in data and JSON
                logger.info(
                    f"item location {item.location} for item {item.name} does not correspond to a room or entity. Resetting it to default location."
                )
                # This will also register the item with the room, and store the update
                item.set_room(self.default_location)
            else:
                # Add item to list of items for its starting room
                self.add_item_to_room(item, item.location)

    # Update item description and store in database
    def update_item_description(self, item: GameItem, description: str) -> None:
        item.description = description
        self.storage_manager.store_game_object(self.name, item)

    def load_entities(self) -> None:
        if self.entities:
            exit(logger, "Load_entities called when entities are already registered!")
        logger.info("Loading entities...")
        for entity_role in ("Animal", "Merchant"):
            for this_item in self.storage_manager.get_game_objects(
                self.name, entity_role
            ):
                logger.debug(f"Loading entity {this_item['name']}")
                # Populate the room_item_map with object versions of the items
                # TODO #79 Streamline merchant and animal DB->object loading
                entity_object: Union[Animal, Merchant]
                if this_item.get("role") == "merchant":
                    entity_object = Merchant(
                        self,
                        name=this_item["name"],
                        location=this_item["location"],
                        inventory=[],
                        description=this_item.get("description", ""),
                    )
                elif this_item.get("role") == "animal":
                    entity_object = Animal(
                        self,
                        name=this_item["name"],
                        location=this_item["location"],
                        description=this_item.get("description", ""),
                        actions=this_item.get("actions", []),
                        action_chance=this_item.get("action_chance", 0.5),
                    )
                else:
                    exit(logger, "Invalid or unsupported entity role")
                self.register_entity(entity_object)
            # Storage empties - load from file
            # TODO #80 Consider moving default data loading from file down from world to storage manager
            if not self.entities:
                logger.info("No stored entities - loading from file instead")
                self.load_default_entities()

    def load_default_entities(self) -> None:
        logger.info("Loading default entities from file")
        entities = self.storage_manager.get_default_world_data(self.name, "entities")
        for entity in entities:
            logger.info(f"Loading {entity['name']}")
            self.spawn_entity(entity)

    # Create entity from dictionary and store in database
    def spawn_entity(self, entity: Entity) -> None:
        entity_object = None
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
        self.register_entity(entity_object)

    def register_entity(self, entity: Union[Merchant, Animal]) -> None:
        # TODO #81 Implement unique entity and object ID to allow ants coins etc
        self.entities[entity.name] = entity

    # Return list of entity names (e.g. for checking valid item starting locations)
    def get_entity_names(self) -> List[str]:
        entity_names: List[str] = []
        for entity in self.entities.values():
            entity_names.append(entity.name)
        return entity_names

    # Update entity description and store in database
    def update_entity_description(self, entity: Entity, description: str) -> None:
        entity.description = description
        self.storage_manager.store_game_object(self.name, entity)

    def get_currency(
        self, amount: Optional[int] = None, short: bool = False, plural: bool = False
    ) -> str:
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

    def create_player(self, sid: str, name: str, role: str) -> Union[str, Player]:
        # Access player's initial state if they have played before.
        stored_player_data = self.storage_manager.get_game_object(
            self.name, object_type="Player", rowkey_value=name
        )
        p: Player = Player(self, sid, name, role, stored_player_data=stored_player_data)
        # Store player's data again (updates last login timestamp if nothing else)
        self.storage_manager.store_game_object(self.name, p)

        # TODO #82 Improve error handling around player creation
        return "", p
