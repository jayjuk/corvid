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
            sid, self.game_server.get_room_description(self.current_room)
        )
        self.seen_rooms[self.current_room] = True

        # Tell other players about this new player
        self.game_server.tell_others(
            sid,
            f"{player_name} has joined the game, starting in the {self.current_room}; there are now {self.game_server.get_player_count()} players.",
            shout=True,
        )
        self.game_server.emit_game_data_update()

    def process_player_input(self, player_input):
        self.last_action_time = time.time()
        player_response = ""
        if player_input:
            words = str(player_input).split()
            command = words[0].lower()
            # get the rest of the response apart from the first word
            rest_of_response = " ".join(words[1:])
            # strip out quotes from the outside of the response only
            if rest_of_response.startswith('"') and rest_of_response.endswith('"'):
                rest_of_response = rest_of_response[1:-1]
            # Do the same for single quotes
            elif rest_of_response.startswith("'") and rest_of_response.endswith("'"):
                rest_of_response = rest_of_response[1:-1]

            command = self.game_server.synonyms.get(command, command)
            log(f"Command: {command}")

            # Call the function associated with a command
            if command in self.game_server.command_functions:
                player_response = self.game_server.command_functions[command](
                    self, rest_of_response
                )
            # Call the function associated with the command
            elif command in self.game_server.directions:
                player_response = self.move_player(command, rest_of_response)
            else:
                # Invalid command
                player_response = (
                    "Sorry, that is not a recognised command. Available commands:\n"
                    + self.game_server.get_commands_description()
                )
        else:
            # Empty command
            player_response = "Sorry, you need to enter a command."
        return player_response

    def move_player(self, direction, next_room=None):
        # Set new room
        previous_room = self.current_room
        if direction == "jump":
            # If next room specified, player has 'jumped'!
            departure_message_to_other_players = (
                f"{self.player_name} has disappeared in a puff of smoke!"
            )
            arrival_message_to_other_players = (
                f"{self.player_name} has materialised as if by magic!"
            )
        elif direction in self.game_server.rooms[self.current_room]["exits"]:
            next_room = self.game_server.rooms[self.current_room]["exits"][direction]

            departure_message_to_other_players = f"{self.player_name} leaves, heading {direction} to the {str(next_room).lower()}."
            arrival_message_to_other_players = (
                f"{self.player_name} arrives from the {previous_room.lower()}."
            )
        else:
            # Valid direction but no exit
            return "Sorry, you can't go that way."

        # Check for other players you are leaving
        for other_player in self.game_server.get_other_players(self.sid):
            if other_player.current_room == self.current_room:
                self.game_server.tell_player(
                    other_player.sid,
                    departure_message_to_other_players,
                )

        # Set new room
        self.current_room = next_room

        self.game_server.update_player_room(self.sid, self.current_room)

        if direction == "jump":
            action = "jumped"
        else:
            action = f"went {direction}"

        # Build message. only describe room if it is new to this player.
        message = f"You {action} to the {str(self.current_room).lower()}"
        if self.current_room in self.seen_rooms:
            message += f". {self.game_server.get_room_description(self.current_room, brief=True)}"
        else:
            message += f": {self.game_server.get_room_description(self.current_room)}"
            self.seen_rooms[self.current_room] = True

        # Check for other players you are arriving
        for other_player in self.game_server.get_other_players(self.sid):
            if other_player.current_room == self.current_room:
                message += f" {other_player.player_name} is here."
                self.game_server.tell_player(
                    other_player.sid,
                    arrival_message_to_other_players,
                )

        return message
