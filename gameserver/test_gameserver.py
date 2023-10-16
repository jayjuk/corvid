import unittest
from gameserver import GameServer


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
        expected_count = 0
        description = game_server.get_commands_description().lower()
        for command in ("north", "south", "east", "west", "look", "say"):
            self.assertIn(
                command, description, f"Command {command} missing from description"
            )
