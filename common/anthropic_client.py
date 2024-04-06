from logger import setup_logger
from typing import List, Dict
import utils
from urllib.request import urlopen

# Set up logger
logger = setup_logger()

# Avoid mixing up loggers by importing third party modules after logger
import anthropic

# Connect to the LLM API
def get_model_client():
    # Use pre-set variable before dotenv.
    utils.check_env_var("ANTHROPIC_API_KEY")
    return anthropic.Anthropic()

# Get the model response (Anthropic specific)
def do_model_request(model_client, messages: List[Dict[str, str]], model_name: str, max_tokens: int, system_message: str) -> str:

    model_response = model_client.messages.create(
        model=model_name,
        max_tokens=max_tokens,
        messages=messages,
        system=system_message,
    )
    return model_response.content[0].text
