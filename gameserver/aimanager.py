import os
from openai import OpenAI

# from openai.types import Image, ImagesResponse
import urllib.request
from dotenv import load_dotenv
from logger import setup_logger

# Set up logging
logger = setup_logger()

load_dotenv()
try:
    client = OpenAI()
    logger.info("Connected to OpenAI API")
    DO_NOT_GENERATE_IMAGES = os.getenv("DO_NOT_GENERATE_IMAGES") or False
except Exception as e:
    logger.error(f"Error connecting to OpenAI API: {e}")
    DO_NOT_GENERATE_IMAGES = True

# TODO: Errors will occur if the functions below are called without the client being set up. For now, just making unit tests pass.
# This is better than connecting to OpenAI in unit testing, but not ideal
# .env is not in Github
# TODO: figure out how to manage keys in Github


# Stateless image manager
def create_image(image_name, description):
    """Create an image from description and return the file name"""
    # make file name from image name, replacing spaces with underscores and lowercasing
    file_name = image_name.lower().replace(" ", "_").replace("'", "") + ".png"
    full_path = os.sep.join(("..", "gameclient", "public", file_name))
    if DO_NOT_GENERATE_IMAGES or os.path.exists(full_path):
        # Let the client handle if a file is missing.
        # Although room name is unique, during testing a room may have been created before
        # And so the image may already exist
        return file_name
    # Create image
    response = client.images.generate(prompt=description, n=1, size="1024x1024")
    image = response.data[0]
    url = image.url
    # Download URL and save to file
    urllib.request.urlretrieve(url, full_path)
    logger.info(f"Generated {file_name}")
    return file_name


def submit_prompt(
    prompt,
    model_name="gpt-3.5-turbo",
    max_tokens=100,
    temperature=0.7,
):
    messages = [
        {
            "role": "user",
            "content": prompt,
        }
    ]

    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        max_tokens=max_tokens,
    )
    print("Raw response:", response)
    for choice in response.choices:
        # Return content of first choice
        return choice.message.content.strip()
