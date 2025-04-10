from typing import List, Dict
from utils import get_critical_env_variable, set_up_logger


# Set up logger
logger = set_up_logger()

# Avoid mixing up loggers by importing third party modules after logger
from groq import Groq


# Connect to the LLM API
def get_model_client() -> Groq:
    # Use pre-set variable before dotenv.

    return Groq(
        api_key=get_critical_env_variable("GROQ_API_KEY"),
    )


# Get the model response (Anthropic specific)
def do_model_request(
    model_client,
    messages: List[Dict[str, str]],
    model_name: str = "mixtral-8x7b-32768",
    max_tokens: int = 1000,
) -> str:

    chat_completion = model_client.chat.completions.create(
        messages=messages,
        model=model_name,
        max_tokens=max_tokens,
    )
    import pprint

    return chat_completion.choices[0].message.content
