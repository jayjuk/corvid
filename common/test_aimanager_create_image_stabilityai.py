import aimanager
from dotenv import load_dotenv
from os import path

load_dotenv(dotenv_path=path.join("..", "common", ".env"))

model_name = "stable-diffusion-xl-1024-v1-0"

ai_manager = aimanager.AIManager(model_name=model_name)

ai_manager.create_image(
    "road",
    "Endless horizons beckon from either direction of this seemingly abandoned road. Sunlight dances on the asphalt, hinting at a time when cars frequented here. Now, only the gentle whisper of wind breaks the stillness.",
)
