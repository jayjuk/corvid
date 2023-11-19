import os
from openai import OpenAI

# from openai.types import Image, ImagesResponse
import urllib.request
from dotenv import load_dotenv
from logger import setup_logger

# Set up logging
logger = setup_logger()

load_dotenv()

client = OpenAI()
DO_NOT_GENERATE_IMAGES = os.getenv("DO_NOT_GENERATE_IMAGES") or False
print(client)


# Stateless image manager
def create_image(image_name, description):
    """Create an image from description and return the file name"""
    # make file name from image name, replacing spaces with underscores and lowercasing
    file_name = image_name.lower().replace(" ", "_").replace("'", "") + ".png"
    if DO_NOT_GENERATE_IMAGES:
        # Let the client  handle missing file
        return file_name
    # Create image
    response = client.images.generate(prompt=description, n=1, size="1024x1024")
    image = response.data[0]
    url = image.url
    # Download URL and save to file
    full_path = os.sep.join(("..", "gameclient", "public", file_name))
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
