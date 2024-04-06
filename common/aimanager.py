import traceback
import os
import json
import time
import sys
from pprint import pprint
from typing import List, Dict, Union, Tuple, Optional, Any
import base64
import json
from logger import setup_logger


# Set up logger
logger = setup_logger()

# TODO #87 Separate different LLMs into subclasses so libraries aren't imported unnecessarily
import openai
from stability_sdk import client
from urllib.request import urlopen
import anthropic
import vertexai
from vertexai.preview.generative_models import (
    GenerativeModel,
    Content,
    Part,
    Candidate,
)
from google.oauth2.service_account import Credentials
from google.cloud.aiplatform_v1beta1.types.content import SafetySetting
from vertexai.preview.generative_models import HarmCategory, HarmBlockThreshold



# Class to handle interaction with the AI
class AIManager:
    def __init__(self, system_message: str = None, model_name: str = None):

        # Static variables
        self.max_history: int = 40
        self.max_wait: int = 7  # secs
        self.last_time: float = time.time()
        self.active: bool = True
        self.input_token_count: int = 0
        self.output_token_count: int = 0

        # Chat history / context
        self.chat_history: List[Dict[str, Union[str, List[Dict[str, str]]]]] = []

        # Event log = feedback from game manager, to be included in next request
        self.event_log: List[str] = []

        # Flag to keep track of whether we have sent a system message for Gemini
        self.first_request: bool = True

        # Model costs as of 22 Feb 2024 from https://openai.com/pricing#language-models
        # Input, output
        self.model_cost: Dict[str, Tuple[float, float]] = {
            "gpt-3.5-turbo": (0.0005, 0.0015),
            "gpt-4-turbo-preview": (0.01, 0.03),
            "gemini-pro": (0, 0),
        }

        # Get model choice from env variable if possible
        self.model_name: str = model_name or os.environ.get("MODEL_NAME") or "gemini-pro"
        logger.info(f"Model name set to {self.model_name}")

        #  Adjust the max_tokens based on desired response length
        self.max_tokens: int = 200
        self.ai_name: Optional[str] = None

        # Flag to prevent image generation
        self.do_not_generate_images: bool = os.environ.get("DO_NOT_GENERATE_IMAGES", False)

        # Set up openAI connection
        # We are going to use the chat interface to get AI To play our text adventure game
        self.model_api_connect()

        # Set system message
        self.system_message: str = system_message or "You are playing an adventure game."

        # Model-specific static
        self.content_word: str = "content"
        self.model_word: str = "assistant"
        self.history_abbreviation_content: str = (
            "(some game transcript history removed for brevity)"
        )
        if self.get_model_api() == "Gemini":
            # Override max history for Gemini for now, as it's free
            self.max_history: int = 99999
            self.model_word: str = "model"
            self.content_word: str = "parts"
        logger.info("Starting up AI with model " + self.model_name)
        # Create specific log file for model responses
        self.create_model_log_file()

    # Set system message
    def set_system_message(self, system_message: str) -> None:
        if system_message:
            logger.info(f"Updating system message to: {system_message}")
            self.system_message = system_message

    # Create a log file for model responses
    def create_model_log_file(self) -> None:
        self.model_log_file: str = f"{self.get_model_api()}_response_log.txt"
        with open(self.model_log_file, "w") as f:
            f.write(f"# Model input and response log for {self.get_model_api()}\n\n")

    # Log model response to file
    def log_response_to_file(self, request: str, response: str) -> None:
        with open(self.model_log_file, "a") as f:
            f.write(f"Request: {request}\nResponse: {response}\n\n")

    # Get the model API name
    # We use the specific model name to generalise which class/company we are using
    def get_model_api(self) -> str:
        if self.model_name.startswith("gpt"):
            return "GPT"
        elif self.model_name.startswith("gemini"):
            return "Gemini"
        elif self.model_name.startswith("claude"):
            return "Anthropic"
        elif self.model_name.startswith("stable-diffusion"):
            return "StabilityAI"

    # Store model data to file (for investigating issues with model responses)
    def store_model_data(self, filename_prefix: str, data: Any) -> None:
        logger.info("Saving model data")
        folder_path: str = "model_io"
        os.makedirs(folder_path, exist_ok=True)
        with open(
            folder_path + os.sep + f"{self.model_name}_{filename_prefix}.tmp",
            "w",
        ) as f:
            json.dump(data, f, indent=4)

    # Check if mandatory environment variable is set
    def check_env_var(self, env_var_name: str) -> None:
        if not os.environ.get(env_var_name):
            self.exit(f"{env_var_name} not set. Exiting.")

    # Connect to the LLM API
    def model_api_connect(self) -> None:
        # Use pre-set variable before dotenv.
        if self.get_model_api() == "GPT":
            self.check_env_var("OPENAI_API_KEY")

            openai.api_key = os.getenv("OPENAI_API_KEY")
            self.model_client = openai.OpenAI()

        elif self.get_model_api() == "Anthropic":
            self.check_env_var("ANTHROPIC_API_KEY")
            self.model_client = anthropic.Anthropic()

        elif self.get_model_api() == "Gemini":
            self.check_env_var("GOOGLE_GEMINI_KEY")

            # Load Base 64 encoded key JSON from env variable and convert back to JSON
            credentials: Dict = json.loads(
                base64.b64decode(os.environ["GOOGLE_GEMINI_KEY"])
            )

            vertexai.init(
                project="jaysgame",
                location="us-central1",
                # This overrides the default use of GOOGLE_APPLICATION_CREDENTIALS containing a file with the key in JSON
                credentials=Credentials.from_service_account_info(credentials),
            )

            safety_settings : Optional[List[SafetySetting]] = None

            if os.environ.get("GOOGLE_GEMINI_SAFETY_OVERRIDE").startswith("Y"):
                logger.info(
                    "Overriding safety controls (recommended with Gemini to avoid false alarms)"
                )
                safety_settings = [
                    SafetySetting(
                        category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                        threshold=HarmBlockThreshold.BLOCK_NONE,
                    ),
                    SafetySetting(
                        category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                        threshold=HarmBlockThreshold.BLOCK_NONE,
                    ),
                    SafetySetting(
                        category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                        threshold=HarmBlockThreshold.BLOCK_NONE,
                    ),
                    SafetySetting(
                        category=HarmCategory.HARM_CATEGORY_HARASSMENT,
                        threshold=HarmBlockThreshold.BLOCK_NONE,
                    ),
                ]
            else:
                logger.warn(
                    "NOT Overriding safety controls - this is recommended with Gemini to avoid false alarms"
                )
            self.model_client = GenerativeModel(
                "gemini-pro", safety_settings=safety_settings
            )
        elif self.get_model_api() == "StabilityAI":

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
            self.exit(f"Model name {self.model_name} not recognised.")

    # Get the model response (OpenAI specific)
    def do_openai_request(
        self, model_name: Optional[str], max_tokens: Optional[int], temperature: float, messages: List[Dict[str, str]]
    ) -> str:

        # If model not specified, use the default for this object
        this_model: str = model_name or self.model_name

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
                    self.content_word: model_response,
                }
            )

            break
        # Get tokens and calculate cost
        self.input_token_count += response.usage.prompt_tokens
        self.output_token_count += response.usage.completion_tokens
        session_cost : float = (
            (self.model_cost.get(this_model, [0])[0] * self.input_token_count / 1000)
            + (self.model_cost.get(this_model, [0])[1] * self.output_token_count / 1000)
        ) / 1.27  # To £
        logger.info(
            f"Tokens used: {response.usage.total_tokens} (input {response.usage.prompt_tokens}, output {response.usage.completion_tokens}). Running total cost: £{session_cost:.2f}"
        )
        return model_response

    # Get the model response (Gemini specific)
    def do_gemini_request(self, messages: List[Dict[str, str]]) -> str:

        model_response = self.model_client.generate_content(messages)
        candidate = model_response.candidates[0]
        if candidate.finish_reason.name != "STOP":
            logger.error(f"Model has issue: {str(model_response)}")
        else:
            return candidate.content.parts[0].text
        return ""

    # Get the model response (Anthropic specific)
    def do_anthropic_request(self, messages: List[Dict[str, str]]) -> str:

        model_response = self.model_client.messages.create(
            model=self.model_name,
            max_tokens=self.max_tokens,
            messages=messages,
            system=self.system_message,
        )
        return model_response.content[0].text

    # Build a message for the model
    def build_message(self, role: str, content: str) -> Union[Dict[str, str], Content]:
        if self.get_model_api() == "Gemini":
            return Content(role=role, parts=[Part.from_text(content)])
        else:
            return {"role": role, self.content_word: content}

    # Submit a request to the model
    def submit_request(
        self,
        request: str,
        model_name: Optional[str] = None,
        max_tokens: Optional[int] = 1000,
        temperature: float = 0.7,
        history: bool = True,
    ) -> str:
        try_count: int = 0
        max_tries: int = 10
        wait_time: int = 5
        logger.info(f"Received request to submit: {request}")

        # Start with system message
        # Gemini
        messages: List = []
        if self.get_model_api() == "Gemini":
            messages = [self.build_message("user", self.system_message)]
            messages.append(self.build_message(self.model_word, "OK."))
        elif self.get_model_api() == "Anthropic":
            pass #Leave empty
        else:
            messages = [self.build_message("system", self.system_message)]

        # Now use history to build the messages for model input
        # (we have a separate messages list to allow for model-specific truncation without losing the history from our own memory,
        # for example in case we want to dump it later for diagnostics
        if history:
            if len(self.chat_history) > self.max_history:
                messages.append(
                    self.build_message("user", self.history_abbreviation_content)
                )
                messages.append(self.build_message(self.model_word, "OK."))
            for history_item in self.chat_history[-1 * self.max_history]:
                messages.append(
                    self.build_message(
                        history_item["role"], history_item[self.content_word]
                    )
                )

        # Now add request
        messages.append(self.build_message("user", request))

        logger.info(
            f"About to submit to model, with system message: {self.system_message}"
        )

        # Get model response, retrying if necessary
        model_response: Optional[str] = None
        while not model_response and try_count < max_tries:
            try_count += 1
            try:
                # Behaviour varies according to model type.
                if self.model_name.startswith("gpt"):

                    model_response = self.do_openai_request(
                        model_name=model_name,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        messages=messages,
                    )
                elif self.get_model_api() == "Gemini":
                    model_response = self.do_gemini_request(messages)
                elif self.get_model_api() == "Anthropic":
                    model_response = self.do_anthropic_request(messages)
                else:
                    self.exit(f"Unsupported model type: {self.model_name}")

            except Exception as e:
                traceback.print_exc()
                logger.info(f"Error from model: {str(e)}")
                if (
                    "server is overloaded" in str(e)
                    or "The response was blocked." in str(e)
                    or "list index out of range" in str(e)
                    or "rate_limit_error" in str(e)
                ) and try_count < max_tries:
                    wait_time = wait_time * 2
                    logger.info(
                        f"Retrying in {wait_time} seconds... (attempt {try_count+1}/{max_tries})"
                    )
                    time.sleep(int(wait_time))
                else:
                    return ""

        if model_response:
            # Save response to file for fine-tuning purposes
            pass
            # TODO #24 Store log input/output better
            # self.store_model_data("input", messages)
            # self.store_model_data("response", response)

            logger.info("Model Response: " + str(model_response))

            self.log_response_to_file(request, model_response)

            # Add request to history
            if history:
                self.chat_history.append(
                    {
                        "role": "user",
                        self.content_word: request,
                    }
                )
                # Add response to history
                self.chat_history.append(
                    {
                        "role": self.model_word,
                        self.content_word: model_response,
                    }
                )

        return model_response

    # Image creator
    def create_image(self, image_name: str, description: str) -> Tuple[str, bytes]:

        # Common filename definition, kept with the image generation to ensure consistency of format.
        file_name: str = image_name.lower().replace(" ", "_").replace("'", "") + ".png"
        """Create an image from description and return the data"""
        if self.get_model_api() == "GPT":
            response = self.model_client.images.generate(
                prompt=description, n=1, size="512x512"
            )
            image = response.data[0]
            url: str = image.url

            response = urlopen(url)
            return file_name, response.read()  # Return binary data
        elif self.get_model_api() == "StabilityAI":
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
        else:
            self.exit(
                "Image generation using other model APIs than OpenAI and StabilityAI not yet supported!"
            )
        return None, None

    # Graceful exit, specific to AI management cases
    def exit(self, error_message: str) -> None:
        logger.error(error_message + " Exiting.")
        # Write chat_history to file
        with open("exit_chat_history_dump.txt", "w") as f:
            for item in self.chat_history:
                for key, value in item.items():
                    f.write(f"{key}: {value}\n")
        sys.exit()

