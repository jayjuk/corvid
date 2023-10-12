import json
import os
import sys
import openai
import urllib.request
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Read game data from JSON file into a dictionary
with open("..\\gameserver\\map.json", "r") as f:
    game_data = json.load(f)

for location, data in game_data.items():
    description = data["description"]
    image_name = data["image"].replace(".jpg", ".png")

    response = openai.Image.create(prompt=description, n=1, size="1024x1024")

    image = response["data"][0]
    url = image["url"]
    # Download URL and save to file
    urllib.request.urlretrieve(url, image_name)
    print(f"Generated {image_name}")

print("Finished generating images.")
