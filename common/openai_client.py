from typing import List, Dict, Tuple, Union, Optional
from utils import get_critical_env_variable, set_up_logger, exit
from urllib.request import urlopen

# Set up logger
logger = set_up_logger()

# Avoid mixing up loggers by importing third party modules after logger
import openai


# Connect to the LLM API
def get_model_client() -> openai.OpenAI:
    # Use pre-set variable before dotenv.
    openai.api_key = get_critical_env_variable("OPENAI_API_KEY")
    return openai.OpenAI()


# Get the model response (OpenAI specific)
def do_model_request(
    model_client: openai.OpenAI,
    model_name: str,
    max_tokens: int,
    temperature: float,
    messages: List[Dict[str, str]],
) -> Tuple[str, int, int]:

    # Set response format according to the last message containing JSON or not
    response_format: Optional[Dict[str, str]] = None
    if "JSON" in messages[-1]["content"]:
        response_format = {"type": "json_object"}

    # Different parameter name for max tokens from GPT-5 onwards
    # TODO: #120 Improve management of model API versioning
    if model_name.startswith("gpt-10"):
        exit(logger, "Must reconfigure model parameters beyond GPT-9")
    if model_name.startswith("gpt-") and model_name[4] in ("5", "6", "7", "8", "9"):
        if model_name=="gpt-5-mini" and temperature!=1:
            logger.warning(f"Overriding temperature to 1 as other values not supported by {model_name}")
            temperature = 1
        response: openai.Response = model_client.chat.completions.create(
            model=model_name,
            messages=messages,
            max_completion_tokens=max_tokens,
            temperature=temperature,
            response_format=response_format,
        )
    else:
        response: openai.Response = model_client.chat.completions.create(
            model=model_name,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format=response_format,
        )

    # Extract response content
    for choice in response.choices:
        return (
            choice.message.content,
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
        )


# Execute image generation request
def do_image_request(model_client: openai.OpenAI, prompt: str) -> Union[bytes, None]:
    response: openai.Response = model_client.images.generate(
        prompt=prompt, n=1, size="512x512"
    )
    if response:
        # Return binary data
        return urlopen(response.data[0].url).read()
