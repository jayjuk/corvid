import unittest
from unittest.mock import patch
from aimanager import AIManager


# Parent class for all AI Manager tests
# Sets up the AI Manager with the specified model name
class TestAIManager(unittest.TestCase):
    def setUp(self) -> None:
        self.ai_manager = AIManager(
            model_name=self.test_model_name, system_message="This is a unit test"
        )


# Each specific LLM test class inherits from the parent class and sets the model name
# But mocks the model client import to avoid importing the actual LLM client library


class TestAIManagerClaude(TestAIManager):

    @patch("anthropic_client.get_model_client")
    def setUp(self, MockModelClient) -> None:
        self.test_model_name = "claude-mock"
        return super().setUp()

    def test_claude(self):
        self.assertEqual(self.ai_manager.model_name, self.test_model_name)


class TestAIManagerGemini(TestAIManager):

    @patch("gemini_client.get_model_client")
    def setUp(self, MockModelClient) -> None:
        self.test_model_name = "gemini-mock"
        return super().setUp()

    def test_gemini(self):
        self.assertEqual(self.ai_manager.model_name, self.test_model_name)


class TestAIManagerOpenAI(TestAIManager):

    @patch("openai_client.get_model_client")
    def setUp(self, MockModelClient) -> None:
        self.test_model_name = "gpt-mock"
        return super().setUp()

    def test_openai(self):
        self.assertEqual(self.ai_manager.model_name, self.test_model_name)


class TestAIManagerStabilityAI(TestAIManager):

    @patch("stability_client.get_model_client")
    def setUp(self, MockModelClient) -> None:
        self.test_model_name = "stable-diffusion-mock"
        return super().setUp()

    def test_stabilityai(self):
        self.assertEqual(self.ai_manager.model_name, self.test_model_name)


class TestAIManagerGroq(TestAIManager):

    @patch("groq_client.get_model_client")
    def setUp(self, MockModelClient) -> None:
        self.test_model_name = "llama-mock"
        return super().setUp()

    def test_groq(self):
        self.assertEqual(self.ai_manager.model_name, self.test_model_name)


if __name__ == "__main__":
    unittest.main()
