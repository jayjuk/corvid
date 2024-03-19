import traceback
import os
import json
import time
import sys
from pprint import pprint

import urllib.request
from logger import setup_logger

# NOTE: OpenAI and Google specific imports are performed during API connection time

# Set up logger
logger = setup_logger()


# Class to handle interaction with the AI
class AIManager:
    def __init__(self, system_message=None, model_name=None):

        self.chat_history = []
        self.event_log = []
        self.max_history = 40
        self.max_wait = 7  # secs
        self.last_time = time.time()
        self.active = True
        self.input_token_count = 0
        self.output_token_count = 0

        # Flag to keep track of whether we have sent a system message for Gemini
        self.first_request = True

        # Model costs as of 22 Feb 2024 from https://openai.com/pricing#language-models
        # Input, output
        self.model_cost = {
            "gpt-3.5-turbo": (0.0005, 0.0015),
            "gpt-4-turbo-preview": (0.01, 0.03),
            "gemini-pro": (0, 0),
        }

        # Get model choice from env variable if possible
        self.model_name = model_name or os.environ.get("MODEL_NAME") or "gemini-pro"
        logger.info(f"Model name set to {self.model_name}")

        self.max_tokens = 200  # adjust the max_tokens based on desired response length
        self.ai_name = None

        self.do_not_generate_images = os.environ.get("DO_NOT_GENERATE_IMAGES", False)

        # Set up openAI connection
        # We are going to use the chat interface to get AI To play our text adventure game
        self.model_api_connect()

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
            f.write(f"# Model input and response log for {self.get_model_api()}\n\n")

    def log_response_to_file(self, request, response):
        with open(f"{self.get_model_api()}_response_log.txt", "a") as f:
            f.write(f"Request: {request}\nResponse: {response}\n\n")

    def get_model_api(self):
        # Use the specific model name to generalise which class/company we are using
        if self.model_name.startswith("gpt"):
            return "GPT"
        elif self.model_name.startswith("gemini"):
            return "Gemini"
        elif self.model_name.startswith("stable-diffusion"):
            return "StabilityAI"

    def save_model_data(self, filename_prefix, data):
        logger.info("Saving model data")
        folder_path = "model_io"
        os.makedirs(folder_path, exist_ok=True)
        with open(
            folder_path + os.sep + f"{self.model_name}_{filename_prefix}.tmp",
            "w",
        ) as f:
            json.dump(data, f, indent=4)

    def check_env_var(self, env_var_name):
        if not os.environ.get(env_var_name):
            self.exit(f"{env_var_name} not set. Exiting.")

    def model_api_connect(self):
        # Use pre-set variable before dotenv.
        if self.get_model_api() == "GPT":
            self.check_env_var("OPENAI_API_KEY")

            # Import here so that we don't need to install this module into a Gemini-only runtime
            import openai

            openai.api_key = os.getenv("OPENAI_API_KEY")
            self.model_client = openai.OpenAI()

        elif self.get_model_api() == "Gemini":
            self.check_env_var("GOOGLE_GEMINI_KEY")

            # Installed from (pip install ) google-cloud-aiplatform
            import vertexai
            from vertexai.preview.generative_models import GenerativeModel
            from google.oauth2.service_account import Credentials

            # Other libraries only needed for Google security
            import base64
            import json

            # Load Base 64 encoded key JSON from env variable and convert back to JSON
            credentials_dict = json.loads(
                base64.b64decode(os.environ["GOOGLE_GEMINI_KEY"])
            )

            vertexai.init(
                project="jaysgame",
                location="us-central1",
                # This overrides the default use of GOOGLE_APPLICATION_CREDENTIALS containing a file with the key in JSON
                credentials=Credentials.from_service_account_info(credentials_dict),
            )
            self.model_client = GenerativeModel("gemini-pro")
            self.gemini_chat = self.model_client.start_chat(history=[])
        elif self.get_model_api() == "StabilityAI":
            from stability_sdk import client

            # From https://platform.stability.ai/docs/features/text-to-image#Python
            os.environ["STABILITY_HOST"] = "grpc.stability.ai:443"
            # os.environ["STABILITY_KEY"] - must already be set
            # Set up our connection to the API.
            self.stability_api = client.StabilityInference(
                key=os.environ["STABILITY_KEY"],  # API Key reference.
                verbose=True,  # Print debug messages.
                engine=self.model_name,  # Set the engine to use for generation.
                # Check out the following link for a list of available engines: https://platform.stability.ai/docs/features/api-parameters#engine
            )
        else:
            self.exit(f"ERROR: Model name {self.model_name} not recognised. Exiting.")

    def do_gpt_request(self, request, model_name, max_tokens, temperature, history):
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

        # If model not specified, use the default for this object
        this_model = model_name or self.model_name

        response = self.model_client.chat.completions.create(
            model=this_model,
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
            (self.model_cost.get(this_model, [0])[0] * self.input_token_count / 1000)
            + (self.model_cost.get(this_model, [0])[1] * self.output_token_count / 1000)
        ) / 1.27  # To £
        logger.info(
            f"Tokens used: {response.usage.total_tokens} (input {response.usage.prompt_tokens}, output {response.usage.completion_tokens}). Running total cost: £{session_cost:.2f}"
        )
        return model_response

    def do_gemini_request(self, request):
        # Set up if first time
        if self.first_request:
            self.first_request = False
            # this client manages history, it just takes a string as input
            request = self.system_message + "\n" + request
        else:
            import pprint

            pprint.pprint(self.gemini_chat._history)
        model_response = self.gemini_chat.send_message(request, stream=True)

        r = ""
        if model_response:
            for chunk in model_response:
                print("*", chunk)
                if chunk.candidates:
                    for candidate in chunk.candidates:
                        print("**", candidate)
                        for part in candidate.content.parts:
                            r += part.text + "\n"

        model_response = r.strip("*").strip()
        # If the response contains newline(s) followed by some info in parentheses, strip all this out
        if "\n(" in model_response and model_response.endswith(")"):
            logger.info(
                f"Stripping out extra info from Gemini response. Full response: {model_response}"
            )
            model_response = model_response.split("\n(")[0].strip()
        # Convert all-upper-case response to natural case
        if model_response.isupper():
            model_response = model_response.title()
        return model_response

    def submit_request(
        self,
        request,
        model_name=None,  # Default self.model_name is used elsewhere, but this can be overridden
        max_tokens=1000,
        temperature=0.7,
        history=True,
    ):
        try_count = 0
        model_response = None
        max_tries = 10
        while not model_response and try_count < max_tries:
            try_count += 1
            try:
                # Submit request to LLM
                logger.info("Submitting request to model...")

                # Behaviour varies according to model type.
                if self.model_name.startswith("gpt"):

                    model_response = self.do_gpt_request(
                        request,
                        model_name=model_name,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        history=history,
                    )
                elif self.model_name.startswith("gemini"):
                    model_response = self.do_gemini_request(
                        request,
                    )
                else:
                    self.exit(f"Unsupported model type: {self.model_name}")
            except Exception as e:
                traceback.print_exc()
                logger.info(f"Error from model: {str(e)}")
                if (
                    "server is overloaded" in str(e)
                    or "The response was blocked." in str(e)
                ) and try_count < max_tries:
                    sleep_time = try_count * 5
                    logger.info(
                        f"Retrying in {sleep_time} seconds... (attempt {try_count+1}/{max_tries})"
                    )
                    time.sleep(sleep_time)
                else:
                    return ""

        if model_response:
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

        # Common filename definition, kept with the image generation to ensure consistency of format.
        file_name = image_name.lower().replace(" ", "_").replace("'", "") + ".png"
        """Create an image from description and return the data"""
        if self.get_model_api() == "GPT":
            response = self.model_client.images.generate(
                prompt=description, n=1, size="512x512"
            )
            image = response.data[0]
            url = image.url
            # Download URL and save to file
            # urllib.request.urlretrieve(url, file_name)
            # logger.info(f"Generated {file_name}")
            from urllib.request import urlopen

            response = urlopen(url)
            return file_name, response.read()  # Return binary data
        elif self.get_model_api() == "StabilityAI":
            import io
            import warnings
            from PIL import Image
            import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation

            # Set up our initial generation parameters.
            answers = self.stability_api.generate(
                prompt=description,
                # seed=4253978046,  # If a seed is provided, the resulting generated image will be deterministic.
                # What this means is that as long as all generation parameters remain the same, you can always recall the same image simply by generating it again.
                # Note: This isn't quite the case for Clip Guided generations, which we'll tackle in a future example notebook.
                steps=50,  # Amount of inference steps performed on image generation. Defaults to 30.
                cfg_scale=8.0,  # Influences how strongly your generation is guided to match your prompt.
                # Setting this value higher increases the strength in which it tries to match your prompt.
                # Defaults to 7.0 if not specified.
                width=512,  # Generation width, defaults to 512 if not included.
                height=512,  # Generation height, defaults to 512 if not included.
                samples=1,  # Number of images to generate, defaults to 1 if not included.
                sampler=generation.SAMPLER_K_DPMPP_2M,  # Choose which sampler we want to denoise our generation with.
                # Defaults to k_dpmpp_2m if not specified. Clip Guidance only supports ancestral samplers.
                # (Available Samplers: ddim, plms, k_euler, k_euler_ancestral, k_heun, k_dpm_2, k_dpm_2_ancestral, k_dpmpp_2s_ancestral, k_lms, k_dpmpp_2m, k_dpmpp_sde)
            )

            # Set up our warning to print to the console if the adult content classifier is tripped.
            # If adult content classifier is not tripped, save generated images.
            for resp in answers:
                for artifact in resp.artifacts:
                    if artifact.finish_reason == generation.FILTER:
                        logger.warning(
                            "Your request activated the API's safety filters and could not be processed."
                            + " Please modify the prompt and try again."
                        )
                    if artifact.type == generation.ARTIFACT_IMAGE:
                        return file_name, artifact.binary
                        # with Image.open(io.BytesIO(artifact.binary)) as img:
                        #    img.save(
                        #        file_name
                        #    )  # Save our generated images with their seed number as the filename.
            # return file_name
        else:
            self.exit(
                "Image generation using other model APIs than OpenAI and StabilityAI not yet supported!"
            )
        return None, None

    # Graceful exit, specific to AI management cases
    def exit(self, error_message):
        logger.error(error_message)
        # Write chat_history to file
        with open("exit_chat_history_dump.txt", "w") as f:
            for item in self.chat_history:
                for key, value in item.items():
                    f.write(f"{key}: {value}\n")
        sys.exit()
