import os
import openai
import urllib.request
from dotenv import load_dotenv
from gameutils import log

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
DO_NOT_GENERATE_IMAGES = os.getenv("DO_NOT_GENERATE_IMAGES") or False


# Stateless image manager
def create_image(image_name, description):
    """Create an image from description and return the file name"""
    # make file name from image name, replacing spaces with underscores and lowercasing
    file_name = image_name.lower().replace(" ", "_").replace("'", "") + ".png"
    if DO_NOT_GENERATE_IMAGES:
        # Let the client  handle missing file
        return file_name
    # Create image
    response = openai.Image.create(prompt=description, n=1, size="1024x1024")
    image = response["data"][0]
    url = image["url"]
    # Download URL and save to file
    full_path = os.sep.join(("..", "gameclient", "public", file_name))
    urllib.request.urlretrieve(url, full_path)
    log(f"Generated {file_name}")
    return file_name
