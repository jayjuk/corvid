from typing import Union
import os
import requests
from utils import get_critical_env_variable, set_up_logger


# Set up logger
logger = set_up_logger()


# Get the model client for the specified model (no longer needed, but kept for compatibility)
def get_model_client(model_name: str) -> None:
    logger.info(f"Model name is legacy - using CORE service: {model_name}")
    return None  # Placeholder for compatibility


# Execute image generation request using the new Stability API
def do_image_request(prompt: str) -> Union[bytes, None]:
    api_key = get_critical_env_variable("STABILITY_KEY")
    url = "https://api.stability.ai/v2beta/stable-image/generate/core"
    headers = {
        "authorization": f"Bearer {api_key}",
        "accept": "image/*",
    }
    data = {
        "prompt": prompt,
        # TODO: #117 change from png to webp?
        "output_format": "png",
    }

    try:
        response = requests.post(url, headers=headers, files={"none": ""}, data=data)

        if response.status_code == 200:
            logger.info("Image generation successful.")
            return response.content
        else:
            logger.error(f"Image generation failed: {response.json()}")
            return None
    except Exception as e:
        logger.error(f"An error occurred during the image request: {e}")
        return None
