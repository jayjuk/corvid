import os
import json
import time
import sys
from pprint import pprint

# from openai.types import Image, ImagesResponse
import urllib.request
from dotenv import load_dotenv
from logger import setup_logger

# NOTE: OpenAI and Google specific imports are performed during API connection time, since it is a singleton

# Set up logger
logger = setup_logger()

# Load env variables
# TODO: figure out how to manage keys in Github? .env is not checked in for obvious reasons
load_dotenv()


# Class to handle interaction with the AI


class AIManager:
    def __init__(self, mode="player", system_message=None):

        self.chat_history = []
        self.event_log = []
        self.max_history = 10
        self.max_wait = 7  # secs
        self.last_time = time.time()
        self.active = True
        self.mode = mode
        self.input_token_count = 0
        self.output_token_count = 0

        # Flag to keep track of whether we have sent a system message for Gemini
        self.first_request = True

        # Model costs as of 22 Feb 2024 from https://openai.com/pricing#language-models
        self.input_cost = {
            "gpt-3.5-turbo": 0.0005,
            "gpt-4-turbo-preview": 0.01,
            "gemini-pro": 0,
        }
        self.output_cost = {
            "gpt-3.5-turbo": 0.0015,
            "gpt-4-turbo-preview": 0.03,
            "gemini-pro": 0,
        }

        # Get model choice from env variable if possible
        self.model_name = os.environ.get("MODEL_NAME") or "gpt-3.5-turbo"
        self.max_tokens = 200  # adjust the max_tokens based on desired response length
        self.ai_name = None

        self.do_not_generate_images = os.getenv("DO_NOT_GENERATE_IMAGES") or False

        # Set up openAI connection
        # We are going to use the chat interface to get AI To play our text adventure game
        self.model_api_connect()
        self.mode = mode

        # Set system message
        self.system_message = system_message or "You are playing an adventure game."

        # Override max history for Gemini for now, as it's free
        if self.get_model_api() == "Gemini":
            self.max_history = 99999

        logger.info("Starting up AI with model " + self.model_name)

        self.create_model_log_file()

    def set_system_message(self, system_message):
        if system_message:
            logger.info(f"Updating system message to: {system_message}")
            self.system_message = system_message

    def create_model_log_file(self):
        with open(f"{self.get_model_api()}_response_log.txt", "w") as f:
            f.write(f"# Model input and response log for {self.model_client}\n\n")

    def log_response_to_file(self, request, response):
        with open(f"{self.get_model_api()}_response_log.txt", "a") as f:
            f.write(f"Request: {request}\nResponse: {response}\n\n")

    def get_model_api(self):
        # Use the specific model name to generalise which class/company we are using
        if self.model_name.startswith("gpt"):
            return "GPT"
        elif self.model_name.startswith("gemini"):
            return "Gemini"

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
                    self.exit("OPENAI_API_KEY not set. Exiting.")

            # Import here so that we don't need to install this module into a Gemini-only runtime
            import openai

            openai.api_key = os.getenv("OPENAI_API_KEY")
            self.model_client = openai.OpenAI()
        elif self.get_model_api() == "Gemini":
            # If env variable not set and file exists, set it
            # set GOOGLE_APPLICATION_CREDENTIALS=
            gcloud_credentials_file = "gemini.key"
            if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
                if not os.path.exists(gcloud_credentials_file):
                    self.exit(
                        f"GOOGLE_APPLICATION_CREDENTIALS not set and {gcloud_credentials_file} does not exist"
                    )
                else:
                    logger.info(
                        "Setting GOOGLE_APPLICATION_CREDENTIALS to {}".format(
                            gcloud_credentials_file
                        )
                    )
                    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
                        gcloud_credentials_file
                    )

            # Installed from (pip install ) google-cloud-aiplatform
            import vertexai
            from vertexai.preview.generative_models import GenerativeModel

            vertexai.init(project="jaysgame", location="us-central1")
            self.model_client = GenerativeModel("gemini-pro")
            self.chat = self.model_client.start_chat(history=[])

        else:
            self.exit(f"ERROR: Model name {self.model_name} not recognised. Exiting.")

    def submit_request(
        self,
        request,
        model_name="gpt-3.5-turbo",
        max_tokens=1000,
        temperature=0.7,
        history=True,
    ):
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

                    # Add latest request to history
                    self.chat_history.append(
                        {
                            "role": "user",
                            "content": request,
                        }
                    )

                    # Now use history to build the messages for model input
                    # (we have a separate messages list to allow for model-specific truncation without losing the history from our own memory,
                    # for example in case we want to dump it later for diagnostics
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

                    pprint(messages)

                    response = self.model_client.chat.completions.create(
                        model=(model_name or self.model_name),
                        messages=messages,
                        max_tokens=(max_tokens or self.max_tokens),
                        temperature=temperature,
                    )
                    # Extract response content
                    for choice in response.choices:
                        model_response = choice.message.content

                        self.chat_history.append(
                            {
                                "role": "assistant",
                                "content": model_response,
                            }
                        )

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
                        # this client manages history, it just takes a string as input
                        request = self.system_message + "\n" + request

                    model_response = self.chat.send_message(request)
                    model_response = model_response.text.strip("*").strip()
                    # If the response contains newline(s) followed by some info in parentheses, strip all this out
                    if "\n(" in model_response and model_response.endswith(")"):
                        logger.info(
                            f"Stripping out extra info from Gemini response. Full response: {model_response}"
                        )
                        model_response = model_response.split("\n(")[0].strip()
                    # Convert all-upper-case response to natural case
                    if model_response.isupper():
                        model_response = model_response.title()
                    break
                else:
                    self.exit(f"Unsupported model type: {self.model_name}")
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
                    return ""

        if response:
            # Save response to file for fine-tuning purposes
            pass
            # TODO: TBD whether we want the input or the output or both
            # self.save_model_data("input", messages)
            # self.save_model_data("response", response)

        logger.info("Model Response: " + str(model_response))

        self.log_response_to_file(request, model_response)

        return model_response

    # Image creator
    def create_image(self, image_name, description):
        """Create an image from description and return the file name"""
        # make file name from image name, replacing spaces with underscores and lowercasing
        file_name = image_name.lower().replace(" ", "_").replace("'", "") + ".png"
        # TODO: consider whether current directory is right, and whether we can move away from file, passing around blob in memory instead
        if self.do_not_generate_images or os.path.exists(file_name):
            # Let the client handle if a file is missing.
            # Although room name is unique, during testing a room may have been created before
            # And so the image may already exist
            return file_name
        # Create image
        if self.get_model_api() == "GPT":
            response = self.model_client.images.generate(
                prompt=description, n=1, size="512x512"
            )
            image = response.data[0]
            url = image.url
            # Download URL and save to file
            urllib.request.urlretrieve(url, file_name)
            logger.info(f"Generated {file_name}")
            return file_name
        else:
            # TODO: support Google image generation
            self.exit("Image generation using Gemini not yet supported!")

    # Graceful exit, specific to AI management cases
    def exit(self, error_message):
        logger.error(error_message)
        # Write chat_history to file
        with open("exit_chat_history_dump.txt", "w") as f:
            for key, value in self.chat_history.items():
                f.write(f"{key}: {value}\n")
        sys.exit(1)
