from typing import List, Dict, Union, Tuple, Optional, Any
import traceback
from os import path, makedirs, environ, sep
import json
import time
import gemini_client
import groq_client
import stability_client
import anthropic_client
import openai_client
from utils import set_up_logger, exit, get_logs_folder

# NOTE: Model-specific clients are imported dynamically in the StabilityAI section

# Set up logger
logger = set_up_logger()


# Class to handle interaction with the AI
class AIManager:
    def __init__(
        self, model_name: str, system_message: str, mbh: object = None
    ) -> None:

        # Static variables
        self.max_history: int = 40
        self.max_wait: int = 7  # secs
        self.last_time: float = time.time()
        self.active: bool = True
        self.input_token_count: int = 0
        self.output_token_count: int = 0
        # Message broker object - only provided to some instances where remote requests are required
        self.mbh = mbh

        # Chat history / context
        self.reset()

        # Event log = feedback from game manager, to be included in next request
        self.event_log: List[str] = []

        # Flag to keep track of whether we have sent a system message for Gemini
        self.first_request: bool = True

        # Model costs as of 22 Feb 2024 from https://openai.com/pricing#language-models
        # Input, output pricing per 1000 tokens
        self.model_cost: Dict[str, Tuple[float, float]] = {
            "gpt-3.5-turbo": (0.0005, 0.0015),
            "gpt-4-turbo": (0.01, 0.03),
            "gpt-4o": (0.005, 0.015),
            "gpt-4o-mini": (0.00015, 0.0006),
            "gemini-pro": (0, 0),
            "claude-3-haiku-20240307": (0.00025, 0.00125),
            "mixtral-8x7b-32768": (0, 0),  # Free on Groq for now
            "llama3-70b-8192": (0, 0),  # Free on Groq for now
        }

        # Get model choice from env variable if necessary
        self.model_name: str = model_name
        logger.info(f"Model name set to {self.model_name}")

        #  Adjust the max_tokens based on desired response length
        self.max_tokens: int = 200
        self.ai_name: Optional[str] = None

        # Flag to prevent image generation
        self.do_not_generate_images: bool = environ.get("DO_NOT_GENERATE_IMAGES", False)

        # Set system message
        self.system_message: str = system_message or ""

        # Set up LLM API connection
        self.model_api_connect()

        # Model-specific static
        self.content_word: str = "content"
        self.model_word: str = "assistant"
        self.history_abbreviation_content: str = (
            "(some game transcript history removed for brevity)"
        )
        if self.get_model_api() == "Gemini":
            self.model_word: str = "model"
            self.content_word: str = "parts"
        logger.info(
            f"Starting up AI with model {self.model_name} and system message {self.system_message}"
        )
        # Create specific log file for model responses
        self.create_model_log_file()

        # Remote requests log
        self.remote_requests: Dict[str, Dict[str, Any]] = {}

    # Reset chat history
    def reset(self) -> None:
        self.chat_history: List[Dict[str, str]] = []

    # Set system message
    def set_system_message(self, system_message: str) -> None:
        if system_message:
            logger.info(f"Updating system message to: {system_message}")
            self.system_message = system_message

    # Create a log file for model responses
    def create_model_log_file(self) -> None:
        makedirs(get_logs_folder(), exist_ok=True)
        self.model_log_file: str = path.join(
            get_logs_folder(), f"{self.get_model_api()}_response_log.txt"
        )
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
        elif self.model_name.startswith("gemini") or self.model_name.startswith(
            "imagen"
        ):
            return "Gemini"
        elif self.model_name.startswith("claude"):
            return "Anthropic"
        elif self.model_name.startswith("stable-diffusion"):
            return "StabilityAI"
        elif self.model_name.startswith("mixtral") or self.model_name.startswith(
            "llama"
        ):
            return "Groq"

    # Store model data to file (for investigating issues with model responses)
    def store_model_data(self, filename_prefix: str, data: Any) -> None:
        logger.info("Saving model data")
        # For now, just treat as logging data. We might want to store it in the DB later.
        makedirs(get_logs_folder(), exist_ok=True)
        with open(
            path.join(get_logs_folder(), f"{self.model_name}_{filename_prefix}.tmp"),
            "w",
        ) as f:
            json.dump(data, f, indent=4)

    # Connect to the LLM API
    def model_api_connect(self) -> None:
        # Use pre-set variable before dotenv.
        if self.get_model_api() == "GPT":
            self.model_client = openai_client.get_model_client()

        elif self.get_model_api() == "Anthropic":
            self.model_client = anthropic_client.get_model_client()

        elif self.get_model_api() == "Gemini":
            self.model_client = gemini_client.get_model_client(
                model_name=self.model_name,
                system_instruction=self.system_message,
            )

        elif self.get_model_api() == "StabilityAI":
            self.model_client = stability_client.get_model_client(
                model_name=self.model_name,
            )
        elif self.get_model_api() == "Groq":
            self.model_client = groq_client.get_model_client()
        else:
            exit(logger, f"Model name {self.model_name} not recognised.")

    # Build a message for the model (everyone but Gemini)
    def build_message(self, role: str, content: str):
        return {"role": role, self.content_word: content}

    # Submit a request to the model
    def submit_request(
        self,
        request: str,
        model_name: Optional[str] = None,
        max_tokens: Optional[int] = 1000,
        temperature: float = 0.7,
        history: bool = True,
        system_message: Optional[str] = None,
        cleanup_output: bool = True,
    ) -> str:
        try_count: int = 0
        max_tries: int = 10
        wait_time: float = 3.0
        this_system_message: str = (
            system_message
            or self.system_message
            or "You are a helpful AI assistant for a game server."
        )

        logger.info(
            f"Received request to submit: {request} with system message: {this_system_message}"
        )

        # Use default values if not provided
        model_name = model_name or self.model_name
        max_tokens = max_tokens or self.max_tokens

        # Gemini has special message builder
        messages: List = []
        if self.get_model_api() == "Gemini":
            build_message = gemini_client.build_message
        else:
            build_message = self.build_message

        # Start with system message
        if self.get_model_api() == "Gemini":
            messages = [
                build_message("user", this_system_message),
                build_message(self.model_word, "OK."),
            ]
        elif self.get_model_api() == "Anthropic":
            pass  # Leave empty
        else:
            messages = [build_message("system", this_system_message)]

        # Now use history to build the messages for model input
        # (we have a separate messages list to allow for model-specific truncation without losing the history from our own memory,
        # for example in case we want to dump it later for diagnostics
        if history:
            if len(self.chat_history) > self.max_history:
                messages.append(
                    build_message("user", self.history_abbreviation_content)
                )
                messages.append(build_message(self.model_word, "OK."))
            for history_item in self.chat_history[-1 * self.max_history :]:
                messages.append(
                    build_message(history_item["role"], history_item[self.content_word])
                )

        # Now add request
        messages.append(build_message("user", request))

        logger.info(
            f"About to submit to model, with system message: {this_system_message}"
        )

        # Get model response, retrying if necessary
        model_response: Optional[str] = None
        prompt_tokens: int = 0
        response_tokens: int = 0
        wait_time: float = 0

        while not model_response and try_count < max_tries:
            try_count += 1
            try:
                # Behaviour varies according to model type.
                if self.model_name.startswith("gpt"):

                    model_response, prompt_tokens, response_tokens = (
                        openai_client.do_model_request(
                            model_client=self.model_client,
                            model_name=model_name,
                            max_tokens=max_tokens,
                            temperature=temperature,
                            messages=messages,
                        )
                    )
                elif self.get_model_api() == "Gemini":
                    model_response = gemini_client.do_request(
                        model_client=self.model_client, messages=messages
                    )
                elif self.get_model_api() == "Anthropic":
                    model_response = anthropic_client.do_model_request(
                        model_client=self.model_client,
                        messages=messages,
                        model_name=model_name,
                        max_tokens=max_tokens,
                        system_message=self.system_message,
                    )
                elif self.get_model_api() == "Groq":
                    model_response = groq_client.do_model_request(
                        model_client=self.model_client,
                        messages=messages,
                        model_name=model_name,
                        max_tokens=max_tokens,
                    )
                else:
                    exit(logger, f"Unsupported model type: {self.model_name}")

                # Clean up response
                if cleanup_output and model_response:
                    if "```" in model_response:
                        model_response = model_response.split("```")[0].strip()

                    # Remove any emojis
                    model_response = model_response.encode("ascii", "ignore").decode()

                    # Remove any leading hash
                    model_response = model_response.lstrip("# ")

                    if "#" in model_response:
                        model_response = model_response.split("#")[0].strip()

            except Exception as e:
                traceback.print_exc()
                logger.info(f"Error from model: {str(e)}")
                if (
                    "server is overloaded" in str(e)
                    or "The response was blocked." in str(e)
                    or "list index out of range" in str(e)
                    or "rate_limit_error" in str(e)
                    or "rate_limit_exceeded" in str(e)
                ) and try_count < max_tries:
                    # Check for a substring like Please try again in 940.714285ms, if so, extract that wait time
                    if "Please try again in" in str(e):
                        wait_time = 0.1 + (
                            float(
                                str(e)
                                .split("Please try again in ")[1]
                                .split("ms")[0]
                                .split("s")[0]
                            )
                            / 1000
                        )
                    else:
                        wait_time = wait_time * 2
                    logger.info(
                        f"Retrying in {wait_time} seconds... (attempt {try_count+1}/{max_tries})"
                    )
                    time.sleep(int(wait_time))
                else:
                    return ""

        if model_response:
            # Save response to file for fine-tuning purposes
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

            # Get tokens and calculate cost
            if prompt_tokens or response_tokens:
                self.input_token_count += prompt_tokens
                self.output_token_count += response_tokens
                session_cost: float = (
                    (
                        self.model_cost.get(model_name, [0, 0])[0]
                        * self.input_token_count
                        / 1000
                    )
                    + (
                        self.model_cost.get(model_name, [0, 0])[1]
                        * self.output_token_count
                        / 1000
                    )
                ) / 1.27  # To £
                logger.info(
                    f"Tokens used: {prompt_tokens + response_tokens} (input {prompt_tokens}, output {response_tokens}). Running total cost: £{session_cost:.2f}"
                )

        else:
            logger.error("Model response is empty")
            self.dump_chat_history()
        return model_response

    async def submit_remote_request(
        self,
        handler,
        player: object,
        request_type: str,
        prompt: str,
        system_message: str = "",
        player_context: Any = "",
    ) -> None:
        request_id = str(player.player_id) + str(time.time())  # Unique request ID
        self.remote_requests[request_id] = {
            "request_id": request_id,
            "request_type": request_type,
            "prompt": prompt,
            "system_message": system_message,
        }
        # Copy the object so that the handler can be added
        emission_dict = self.remote_requests[request_id].copy()
        # Add handler afterwards so it doesn't get sent to the AI, plus other stuff to be used in the handler
        self.remote_requests[request_id]["response_handler"] = handler
        self.remote_requests[request_id]["player"] = player
        self.remote_requests[request_id]["player_context"] = player_context

        from pprint import pprint

        print("********* Remote request *********")
        pprint(self.remote_requests[request_id])

        # Check if we have message helper set up
        if not self.mbh:
            exit(
                logger,
                "This AI Manager does not have a message helper set up for remote requests",
            )

        # Emit the request to the server
        await self.mbh.publish("ai_request", emission_dict)
        logger.info(
            f"Remote request submitted with request_id {request_id}: {self.remote_requests[request_id]}"
        )

    async def process_ai_response(self, data: Dict) -> Tuple[object, str]:
        # Look up the request ID in the remote requests
        request_id = data.get("request_id")
        if request_id not in self.remote_requests:
            exit(logger, f"Unknown request ID in AI response: {request_id}")

        # Output response handler method name
        logger.info(
            f"Processing AI response for request ID {request_id} with data {data}"
        )
        logger.info(f"Handler : {self.remote_requests[request_id]['response_handler']}")

        # Get the response from the AI and pass it to the designated response handler along with the player object and AI response
        if "ai_response" not in data:
            exit(logger, f"AI response not found in data: {data}")
        if data["ai_response"]:
            return_text = await self.remote_requests[request_id]["response_handler"](
                data["ai_response"], self.remote_requests[request_id]
            )
        else:
            logger.error(f"AI response is empty for request ID {request_id}")
            return_text = ""
        player = self.remote_requests[request_id]["player"]
        logger.info(f"Deleting request ID {request_id} from remote requests")
        del self.remote_requests[request_id]
        return player, return_text

    # Image creator
    def create_image(self, image_name: str, description: str) -> Tuple[str, bytes]:

        # TODO #94 Handle quota exceeded errors esp from Gemini - different per model?

        # Common filename definition, kept with the image generation to ensure consistency of format.
        file_name: str = image_name.lower().replace(" ", "_").replace("'", "") + ".png"
        """Create an image from description and return the data"""
        if self.get_model_api() == "GPT":
            return file_name, openai_client.do_image_request(
                model_client=self.model_client, prompt=description
            )
        elif self.get_model_api() == "StabilityAI":
            return file_name, stability_client.do_image_request(
                model_client=self.model_client, prompt=description
            )
        elif self.get_model_api() == "Gemini":
            return file_name, gemini_client.do_image_request(prompt=description)
        else:
            exit(
                logger,
                "Image generation using other model APIs than OpenAI and StabilityAI not yet supported!",
            )
        return None, None

    # Graceful exit, specific to AI management cases
    def dump_chat_history(self) -> None:
        # Write chat_history to file
        with open("exit_chat_history_dump.txt", "w") as f:
            for item in self.chat_history:
                for key, value in item.items():
                    f.write(f"{key}: {value}\n")
