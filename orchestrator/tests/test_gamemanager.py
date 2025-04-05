import unittest
from worldmanager import worldmanager
from player import Player
from storagemanager import StorageManager
from player_input_processor import PlayerInputProcessor
import asyncio


class Testworldmanager(unittest.TestCase):
    def setUp(self):
        print("*** Setting up ***")
        self.storage_manager = StorageManager()
        self.world_manager = worldmanager(
            mbh=None,
            storage_manager=self.storage_manager,
            world_name="unittest",
        )
        self.player_input_processor = PlayerInputProcessor(self.world_manager)
        self.player = Player(self.world_manager.world, 0, "TestPlayer")

    def tearDown(self):
        self.world_manager.remove_player(self.player.player_id, "Cleanup after testing")

    def test_get_player_count(self):
        expected_count = 0
        actual_count = self.world_manager.get_player_count()
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
        description = self.world_manager.do_look(self.player, None)
        # Check begins with "You are in"
        self.assertTrue(
            description.startswith("You look again at the"), "Look command not working"
        )
        # Check min length of description
        self.assertGreater(len(description), 28, "Description too short")

    async def test_do_say(self):
        player = Player(self.world_manager.world, 0, "TestPlayer")
        description = await self.world_manager.do_say(player, "Hello")
        self.assertEqual(
            description,
            "You mutter to yourself, 'Hello'.",
            "Say command not working as expected",
        )


if __name__ == "__main__":
    unittest.main()
