import unittest
from unittest.mock import patch, call
from aibroker import AIBroker
import socketio


class TestAIBroker(unittest.TestCase):

    @patch.object(socketio, "Client")
    @patch("aibroker.AIManager")
    def setUp(self, MockAIManager, MockSocketIOClient):

        # Create a new mock instance for this test
        self.mock_ai_manager = MockAIManager.return_value
        self.mock_socketio_client = MockSocketIOClient.return_value

        # Name must be one word for AI Broker  to accept it
        # Invalid name used in a later test, but set up here to keep with valid name
        self.test_invalid_name = "Johnny NonValid"
        self.test_valid_name = "Validius"
        self.mock_ai_manager.submit_request.return_value = self.test_valid_name

        # Create an AI broker that uses the mock AIManager
        self.ai_broker = AIBroker(mode="player")

        # Check that the AIManager was called with the expected system_message
        MockAIManager.assert_called_once_with(
            system_message=self.ai_broker.get_ai_instructions(), model_name=None
        )

    def test_get_player_name(self):
        # Check that the player_name was set correctly
        self.assertEqual(self.ai_broker.player_name, self.test_valid_name)

    def test_record_instructions(self):
        # Check that the player instructions were set correctly
        test_instructions = "Test instructions"
        self.ai_broker.record_instructions(test_instructions)
        self.assertIn(test_instructions, self.ai_broker.game_instructions)
        # Check that the AIManager was called with the expected system_message
        self.mock_ai_manager.set_system_message.assert_called_once()

    def test_get_ai_instructions(self):
        # Check that the player_name was set correctly
        self.assertIn("instructions", self.ai_broker.get_ai_instructions().lower())

    def test_set_ai_name(self):
        # Set up side_effect to return a name with a space, then a valid name
        self.mock_ai_manager.submit_request.player_ide_effect = [
            self.test_invalid_name,
            self.test_valid_name,
        ]

        # Call set_ai_name and check the result
        ai_name = self.ai_broker.set_ai_name()
        self.assertEqual(ai_name, self.test_valid_name)

        # Check that submit_request was called three times (including in setup when constructor was called)
        self.assertEqual(self.mock_ai_manager.submit_request.call_count, 3)

    def test_log_event(self):
        print("test_log_event", self.ai_broker.event_log)
        # Check that the event log is empty
        self.assertEqual(len(self.ai_broker.event_log), 0)
        # Add some events to the log and check each time it increases nicely
        for i in range(1, 6):
            test_event = f"Event {i}"
            self.ai_broker.log_event(test_event)
            self.assertEqual(len(self.ai_broker.event_log), i)
            # Check that the last entry in the log contains the latest test event
            self.assertEqual(test_event, self.ai_broker.event_log[-1])

    # Test clear event log
    def test_clear_event_log(self):
        # Add some events to the log
        for i in range(1, 4):
            test_event = f"Event {i}"
            self.ai_broker.log_event(test_event)
        # Check that the event log is not empty
        self.assertNotEqual(len(self.ai_broker.event_log), 0)
        # Clear the event log
        self.ai_broker.clear_event_log()
        print("Cleared event log:", self.ai_broker.event_log)
        # Check that the event log is empty
        self.assertEqual(len(self.ai_broker.event_log), 0)

    # Test submit_input
    def test_submit_input(self):
        # Set up side_effect to return a name with a space, then a valid name
        test_ai_output = "Test output"
        self.mock_ai_manager.submit_request.return_value = test_ai_output

        # Call submit_input and check the result
        ai_input = "Test input"
        self.ai_broker.log_event(ai_input)
        ai_output = self.ai_broker.submit_input()
        # Check ai_input is part of the request to submit_request
        self.assertIn(ai_input, self.mock_ai_manager.submit_request.call_args[0][0])
        # Check ai_input is part of the return value
        self.assertIn(ai_output, test_ai_output)
        # Check event log cleared
        self.assertEqual(len(self.ai_broker.event_log), 0)

    # Test poll_event_log
    @patch("socketio.Client.emit")
    def test_poll_event_log(self, mock_emit):
        # Add some events to the log
        test_event = "Test event"
        self.ai_broker.log_event(test_event)
        # Poll the event log
        test_ai_output = "Test output"
        self.mock_ai_manager.submit_request.return_value = test_ai_output

        self.ai_broker.poll_event_log()
        # Check that the event log is empty
        self.assertEqual(len(self.ai_broker.event_log), 0)
        # Check the mock emit was called with the expected event
        mock_emit.assert_called_once_with("user_action", test_ai_output)


if __name__ == "__main__":
    unittest.main()
