import unittest
from worldmanager import worldmanager
from person import Person
from storagemanager import StorageManager
from user_input_processor import UserInputProcessor
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
        self.user_input_processor = UserInputProcessor(self.world_manager)
        self.person = Person(self.world_manager.world, 0, "TestPerson")

    def tearDown(self):
        self.world_manager.remove_person(self.person.user_id, "Cleanup after testing")

    def test_get_user_count(self):
        expected_count = 0
        actual_count = self.world_manager.get_user_count()
        self.assertEqual(
            actual_count, expected_count, "Person count should be 0 at start"
        )

    def test_get_commands_description(self):
        description = self.user_input_processor.get_commands_description().lower()
        for command in ("north", "south", "east", "west", "look", "say"):
            self.assertIn(
                command, description, f"Command {command} missing from description"
            )

    def test_do_look(self):
        description = self.world_manager.do_look(self.person, None)
        # Check begins with "You are in"
        self.assertTrue(
            description.startswith("You look again at the"), "Look command not working"
        )
        # Check min length of description
        self.assertGreater(len(description), 28, "Description too short")

    async def test_do_say(self):
        person = Person(self.world_manager.world, 0, "TestPerson")
        description = await self.world_manager.do_say(person, "Hello")
        self.assertEqual(
            description,
            "You mutter to yourself, 'Hello'.",
            "Say command not working as expected",
        )


if __name__ == "__main__":
    unittest.main()
