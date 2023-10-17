import unittest
from gameserver import GameServer, Player


class TestGameServer(unittest.TestCase):
    def test_get_player_count(self):
        game_server = GameServer()
        expected_count = 0
        actual_count = game_server.get_player_count()
        self.assertEqual(
            actual_count, expected_count, "Player count should be 0 at start"
        )

    def test_get_commands_description(self):
        game_server = GameServer()
        description = game_server.get_commands_description().lower()
        for command in ("north", "south", "east", "west", "look", "say"):
            self.assertIn(
                command, description, f"Command {command} missing from description"
            )

    def test_do_look(self):
        game_server = GameServer()
        player = Player(game_server, 0, "Test Player")
        description = game_server.do_look(player, None)
        # Check begins with "You are in"
        self.assertTrue(
            description.startswith("You look again at the"), "Look command not working"
        )
        # Check min length of description
        self.assertGreater(len(description), 28, "Description too short")
        game_server.remove_player(player.sid, "Cleanup after testing")

    def test_do_say(self):
        game_server = GameServer()
        player = Player(game_server, 0, "Test Player")
        description = game_server.do_say(player, "Hello")
        self.assertEqual(
            description,
            "You are the only player in the game currently!",
            "Say command not working as expected",
        )
        game_server.remove_player(player.sid, "Cleanup after testing")


if __name__ == "__main__":
    unittest.main()
