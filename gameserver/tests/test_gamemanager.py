import unittest
from gamemanager import GameManager
from player import Player
from storagemanager import StorageManager
from player_input_processor import PlayerInputProcessor


class TestGameManager(unittest.TestCase):
    def setUp(self):
        print("*** Setting up ***")
        self.storage_manager = StorageManager()
        self.game_manager = GameManager(
            mbh=None,
            storage_manager=self.storage_manager,
            world_name="unittest",
        )
        self.player_input_processor = PlayerInputProcessor(self.game_manager)
        self.player = Player(self.game_manager.world, 0, "TestPlayer")

    def tearDown(self):
        self.game_manager.remove_player(self.player.player_id, "Cleanup after testing")

    def test_get_player_count(self):
        expected_count = 0
        actual_count = self.game_manager.get_player_count()
        self.assertEqual(
            actual_count, expected_count, "Player count should be 0 at start"
        )

    def test_get_commands_description(self):
        description = self.player_input_processor.get_commands_description().lower()
        for command in ("north", "south", "east", "west", "look", "say"):
            self.assertIn(
                command, description, f"Command {command} missing from description"
            )

    def test_do_look(self):
        description = self.game_manager.do_look(self.player, None)
        # Check begins with "You are in"
        self.assertTrue(
            description.startswith("You look again at the"), "Look command not working"
        )
        # Check min length of description
        self.assertGreater(len(description), 28, "Description too short")

    def test_do_say(self):
        player = Player(self.game_manager.world, 0, "TestPlayer")
        description = self.game_manager.do_say(player, "Hello")
        self.assertEqual(
            description,
            "There is no one else here to hear you!",
            "Say command not working as expected",
        )


if __name__ == "__main__":
    unittest.main()
