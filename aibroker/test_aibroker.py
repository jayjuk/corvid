import unittest
from unittest.mock import patch, MagicMock
from aibroker import catch_all, connect, disconnect, main


class TestAIBroker(unittest.TestCase):
    @patch("aibroker.log")
    def test_catch_all(self, mock_log):
        catch_all("test_event", "test_data")
        mock_log.assert_called_once_with("Received other event 'test_event': test_data")

    @patch("aibroker.sio")
    def test_connect(self, mock_sio):
        connect()
        mock_sio.emit.assert_called_once_with("set_player_name", "AI")

    @patch("aibroker.log")
    def test_disconnect(self, mock_log):
        disconnect()
        mock_log.assert_called_once_with("Disconnected from Server.")

    @patch("aibroker.sio")
    def test_main(self, mock_sio):
        mock_ai_manager = MagicMock()
        with patch("aibroker.AIManager", return_value=mock_ai_manager):
            main()
            mock_sio.connect.assert_called_once_with("http://localhost:3001")
            mock_sio.wait.assert_called_once()
            mock_ai_manager.run.assert_called_once()
