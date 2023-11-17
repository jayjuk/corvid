class Character:
    # World reference applies to all character
    world = None

    def __init__(self, world, character_name, character_role, starting_room):
        # Register game server reference in player object to help with testing and minimise use of globals
        if Character.world is None and world is not None:
            Character.world = world

        self.name = character_name
        self.role = character_role

        # Default starting location
        self.current_room = starting_room

        # Inventory
        self.inventory = []

    # Setter for player's location change
    def move_to_room(self, next_room):
        # Set new room
        self.current_room = next_room
        # Flag this room as seen
        self.seen_rooms[self.current_room] = True

    # Getter for player's current location
    def get_current_room(self):
        return self.current_room

    # Setter for player picking up an object
    def add_object(self, object):
        self.inventory.append(object)

    # Setter for player dropping an object
    def drop_object(self, object_name):
        for object in self.inventory:
            if object.get_name().lower() == object_name.lower():
                self.inventory.remove(object)
                object.set_room(self.current_room)
                return object

    def get_inventory(self):
        return self.inventory
