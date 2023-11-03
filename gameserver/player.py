import time
from gameutils import log


class Player:
    def __init__(self, game_server, sid, player_name):
        # Registering game server reference in player object to help with testing and minimise use of globals
        self.game_server = game_server
        self.last_action_time = time.time()
        self.player_name = player_name
        self.current_room = "Road"
        self.seen_rooms = {}
        self.sid = sid
        self.game_server.register_player(sid, self, player_name)
        self.game_server.update_player_room(self.sid, self.current_room)
        instructions = (
            f"Welcome to the game, {player_name}. "
            + self.game_server.get_players_text()
            + "Please input one of these commands:\n"
            + self.game_server.get_commands_description()
        )
        for line in instructions.split("\n"):
            if line:
                self.game_server.tell_player(self.sid, line, type="instructions")

        # Tell this player where they are
        self.game_server.tell_player(
            sid, self.game_server.world.get_room_description(self.current_room)
        )
        self.seen_rooms[self.current_room] = True

        # Tell other players about this new player
        self.game_server.tell_others(
            sid,
            f"{player_name} has joined the game, starting in the {self.current_room}; there are now {self.game_server.get_player_count()} players.",
            shout=True,
        )
        self.game_server.emit_game_data_update()

    def update_last_action_time(self):
        self.last_action_time = time.time()

    # TODO: Decide, does this belong in this class?
    def move_to_room(self, next_room):
        # Set new room
        self.current_room = next_room
        # Flag this room as seen
        self.seen_rooms[self.current_room] = True

    def get_current_room(self):
        return self.current_room
