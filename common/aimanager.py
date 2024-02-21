import os
from openai import OpenAI

# from openai.types import Image, ImagesResponse
import urllib.request
from dotenv import load_dotenv
from logger import setup_logger

# TODO: move this out to a separate class etc, should not import both then only use one
import openai
from google.cloud import aiplatform_v1
import vertexai
from vertexai.preview.generative_models import GenerativeModel
import json
import time
import sys

# Set up logger
logger = setup_logger()

# Load env variables
load_dotenv()


class AIManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            # TODO: check how to do singletones properly, and possibly move constructor logic to __init__
            cls._instance = super(AIManager, cls).__new__(cls)
        try:
            cls._instance.client = OpenAI()
            logger.info("Connected to OpenAI API")
            cls._instance.do_not_generate_images = (
                os.getenv("DO_NOT_GENERATE_IMAGES") or False
            )
        except Exception as e:
            logger.error(f"Error connecting to OpenAI API: {e}")
            cls._instance.do_not_generate_images = True

        # TODO: Errors will occur if the functions below are called without the client being set up. For now, just making unit tests pass.
        # This is better than connecting to OpenAI in unit testing, but not ideal
        # .env is not in Github
        # TODO: figure out how to manage keys in Github

        return cls._instance

    # Image creator
    def create_image(self, image_name, description):
        """Create an image from description and return the file name"""
        # make file name from image name, replacing spaces with underscores and lowercasing
        file_name = image_name.lower().replace(" ", "_").replace("'", "") + ".png"
        full_path = os.sep.join(("..", "gameclient", "public", file_name))
        if self.do_not_generate_images or os.path.exists(full_path):
            # Let the client handle if a file is missing.
            # Although room name is unique, during testing a room may have been created before
            # And so the image may already exist
            return file_name
        # Create image
        response = self.client.images.generate(
            prompt=description, n=1, size="1024x1024"
        )
        image = response.data[0]
        url = image.url
        # Download URL and save to file
        urllib.request.urlretrieve(url, full_path)
        logger.info(f"Generated {file_name}")
        return file_name

    def submit_prompt(
        self,
        prompt,
        model_name="gpt-3.5-turbo",
        max_tokens=100,
    ):
        messages = [
            {
                "role": "user",
                "content": prompt,
            }
        ]

        response = self.client.chat.completions.create(
            model=model_name,
            messages=messages,
            max_tokens=max_tokens,
        )
        logger.debug(f"Raw response:\n{response}")
        for choice in response.choices:
            # Return content of first choice
            return choice.message.content.strip()


# Class to handle interaction with the AI
class AIManager_broker_legacy:
    _instance = None
    chat_history = []
    event_log = []
    max_history = 10
    max_wait = 5  # secs
    last_time = time.time()
    active = True
    mode = None
    input_token_count = 0
    output_token_count = 0
    system_message = "You are playing an adventure game. "
    # Flag to keep track of whether we have sent a system message for Gemini
    first_request = True

    # Model costs as of 29 Jan 2024
    input_cost = {
        "gpt-3.5-turbo-1106": 0.001,
        "gpt-4-0125-preview": 0.01,
        "gemini-pro": 0,
    }
    output_cost = {
        "gpt-3.5-turbo-1106": 0.002,
        "gpt-4-0125-preview": 0.03,
        "gemini-pro": 0,
    }

    # Get model choice from env variable if possible
    model_name = os.environ.get("MODEL_NAME") or "gpt-3.5-turbo-1106"
    # model_name = "gemini-pro"  # "gpt-3.5-turbo"  # "gpt-4" #gpt-3.5-turbo-1106 #gpt-4-0125-preview #gpt-4-1106-preview
    max_tokens = 200  # adjust the max_tokens based on desired response length
    ai_name = None

    def __new__(cls, mode="player", system_message=None):
        if cls._instance is None:
            cls._instance = super(AIManager_broker_legacy, cls).__new__(cls)
            # Set up openAI connection
            # We are going to use the chat interface to get AI To play our text adventure game
            cls._instance.model_api_connect()
            cls._instance.mode = mode
            # Set system message
            cls._instance.system_message = (
                system_message or cls._instance.system_message
            )

            # Override max history for Gemini for now, as it's free
            if cls._instance.get_model_api() == "Gemini":
                cls._instance.max_history = 99999

            logger.info("Starting up AI with model " + cls._instance.model_name)

        return cls._instance

    def get_model_api(self):
        # Use the specific model name to generalise which class/company we are using
        if self.model_name.startswith("gpt"):
            return "GPT"
        elif self.model_name.startswith("gemini"):
            return "Gemini"

    def model_client_manages_history(self):
        if self.get_model_api() == "Gemini":
            return True
        return False

    def save_model_data(self, filename_prefix, data):
        logger.info("Saving model data")
        folder_path = "model_io"
        os.makedirs(folder_path, exist_ok=True)
        with open(
            folder_path + os.sep + f"{self.character_name}_{filename_prefix}.tmp",
            "w",
        ) as f:
            json.dump(data, f, indent=4)

    def model_api_connect(self):
        # Use pre-set variable before dotenv.
        if self.get_model_api() == "GPT":
            if not os.environ.get("OPENAI_API_KEY"):
                load_dotenv()
                if not os.getenv("OPENAI_API_KEY"):
                    logger.info("ERROR: OPENAI_API_KEY not set. Exiting.")
                    sys.exit(1)

            openai.api_key = os.getenv("OPENAI_API_KEY")
            self.model_client = openai.OpenAI()
        elif self.get_model_api() == "Gemini":
            # If env variable not set and file exists, set it
            # set GOOGLE_APPLICATION_CREDENTIALS=
            gcloud_credentials_file = "gemini.key"
            if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
                if not os.path.exists(gcloud_credentials_file):
                    logger.error(
                        "GOOGLE_APPLICATION_CREDENTIALS not set and {} does not exist".format(
                            gcloud_credentials_file
                        )
                    )
                    exit()
                else:
                    logger.info(
                        "Setting GOOGLE_APPLICATION_CREDENTIALS to {}".format(
                            gcloud_credentials_file
                        )
                    )
                    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
                        gcloud_credentials_file
                    )

            vertexai.init(project="jaysgame", location="us-central1")
            self.model_client = GenerativeModel("gemini-pro")
            self.chat = self.model_client.start_chat(history=[])

        else:
            logger.info(f"ERROR: Model name {self.model_name} not recognised. Exiting.")
            sys.exit(1)

    def submit_request(self, request, history=True):
        try_count = 0
        model_response = None
        max_tries = 10
        while not model_response and try_count < max_tries:
            try_count += 1
            response = None
            try:
                # Submit request to LLM
                logger.info(f"Submitting request to model...")

                # Behaviour varies according to model type.
                if self.model_name.startswith("gpt"):

                    # Now use history to build the messages for model input
                    messages = [{"role": "system", "content": self.system_message}]
                    if history:
                        if len(self.chat_history) > self.max_history:
                            messages.append(
                                {
                                    "role": "user",
                                    "content": "(some game transcript history removed for brevity))",
                                }
                            )
                        for history_item in self.chat_history[-1 * self.max_history :]:
                            messages.append(
                                {
                                    "role": history_item["role"],
                                    "content": history_item["content"],
                                }
                            )

                        messages.append({"role": "user", "content": request})

                    response = self.model_client.chat.completions.create(
                        model=self.model_name,
                        messages=messages,
                        max_tokens=self.max_tokens,
                    )
                    # Extract response content
                    for choice in response.choices:
                        model_response = choice.message.content
                        break
                    # Get tokens and calculate cost
                    self.input_token_count += response.usage.prompt_tokens
                    self.output_token_count += response.usage.completion_tokens
                    session_cost = (
                        (
                            self.input_cost.get(self.model_name, 0)
                            * self.input_token_count
                            / 1000
                        )
                        + (
                            self.output_cost.get(self.model_name, 0)
                            * self.output_token_count
                            / 1000
                        )
                    ) / 1.27  # To £
                    logger.info(
                        f"Tokens used: {response.usage.total_tokens} (input {response.usage.prompt_tokens}, output {response.usage.completion_tokens}). Running total cost: £{session_cost:.2f}"
                    )
                elif self.model_name.startswith("gemini"):

                    # Set up if first time
                    if self.first_request:
                        self.first_request = False
                        # Assume that if the client manages history, it just takes a string as input
                        if self.model_client_manages_history():
                            request = self.system_message + "\n" + request

                    # logger.info("FINAL GEMINI INPUT:\n" + message_to_send)
                    model_response = self.chat.send_message(request)
                    # logger.info("ORIGINAL GEMINI RESPONSE:\n" + str(model_response))
                    model_response = model_response.text.strip("*").strip()
                    # If the response contains newline(s) followed by some info in parentheses, strip all this out
                    if "\n(" in model_response and model_response.endswith(")"):
                        model_response = model_response.split("\n")[0].strip()
                    # Convert all-upper-case response to natural case
                    if model_response.isupper():
                        model_response = model_response.title()
                    break
            except Exception as e:
                if (
                    "server is overloaded" in str(e)
                    or "The response was blocked." in str(e)
                ) and try_count < max_tries:
                    logger.info(f"Error from model: {str(e)}")
                    sleep_time = try_count * 5
                    logger.info(
                        f"Retrying in {sleep_time} seconds... (attempt {try_count+1}/{max_tries})"
                    )
                    time.sleep(sleep_time)
                else:
                    logger.info(f"Error from model: {str(e)}")
                    return "exit"

        if response:
            # Save response to file for fine-tuning purposes
            pass
            # TODO: TBD whether we want the input or the output or both
            # self.save_model_data("input", messages)
            # self.save_model_data("response", response)

        logger.info("Model Response: " + str(model_response))

        return model_response
