from logger import setup_logger
from typing import List, Dict
import utils
from urllib.request import urlopen

# Set up logger
logger = setup_logger()

# Avoid mixing up loggers by importing third party modules after logger
import openai

# Connect to the LLM API
def get_model_client():
    # Use pre-set variable before dotenv.
    openai.api_key = utils.get_critical_env_variable("OPENAI_API_KEY")
    return openai.OpenAI()

# Get the model response (OpenAI specific)
def do_model_request(model_client, 
    model_name: str, max_tokens: int, temperature: float, messages: List[Dict[str, str]],
) -> str:

    response = model_client.chat.completions.create(
        model=model_name,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    # Extract response content
    for choice in response.choices:
        return choice.message.content, response.usage.prompt_tokens, response.usage.completion_tokens

# Image creator
def do_image_request(model_client, prompt: str):
    response = model_client.images.generate(
        prompt=prompt, n=1, size="512x512"
    )
    if response:
        # Return binary data
        return urlopen(response.data[0].url).read()
