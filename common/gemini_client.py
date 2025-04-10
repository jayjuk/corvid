import os
from typing import List, Dict, Union, Iterable
import json
import base64
from typing import Optional
from utils import get_critical_env_variable, set_up_logger
from io import BytesIO
from pprint import pprint


# Set up logger
logger = set_up_logger()

# Avoid mixing up loggers by importing third party modules after logger
import vertexai
from vertexai.generative_models import (
    GenerativeModel,
    GenerationResponse,
    Content,
    Part,
    Candidate,
)
from vertexai.vision_models import ImageGenerationModel, ImageGenerationResponse

from google.oauth2.service_account import Credentials
from google.cloud.aiplatform_v1beta1.types.content import SafetySetting
from vertexai.generative_models import HarmCategory, HarmBlockThreshold
from vertexai.vision_models import ImageGenerationModel


# Connect to the LLM API
def get_model_client(model_name: str, system_instruction: str) -> GenerativeModel:

    # Load Base 64 encoded key JSON from env variable and convert back to JSON
    credentials: Dict = json.loads(
        base64.b64decode(get_critical_env_variable("GOOGLE_GEMINI_KEY"))
    )

    vertexai.init(
        project=get_critical_env_variable("GOOGLE_GEMINI_PROJECT_ID"),
        location=get_critical_env_variable("GOOGLE_GEMINI_LOCATION"),
        # This overrides the default use of GOOGLE_APPLICATION_CREDENTIALS containing a file with the key in JSON
        credentials=Credentials.from_service_account_info(credentials),
    )

    safety_settings: Optional[List[SafetySetting]] = None

    if os.environ.get("GOOGLE_GEMINI_SAFETY_OVERRIDE").startswith("Y"):
        logger.info(
            "Overriding safety controls (recommended with Gemini to avoid false alarms)"
        )

        # Set safety settings to block some categories
        threshold: str = HarmBlockThreshold.BLOCK_ONLY_HIGH

        safety_settings = [
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=threshold,
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=threshold,
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=threshold,
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=threshold,
            ),
        ]
    return GenerativeModel(
        model_name=model_name,
        system_instruction=[system_instruction],
        safety_settings=safety_settings,
    )


# Build a message for the model
def build_message(role: str, content: str) -> Union[Dict[str, str], Content]:
    return Content(role=role, parts=[Part.from_text(content)])


# Get the model response (Gemini specific)
def do_request(model_client: GenerativeModel, messages: List[Dict[str, str]]) -> str:
    if os.environ.get("MODEL_DEBUG_MODE", "False").upper() == "TRUE":
        logger.info("Messages sent to model:")
        pprint(messages)

    model_response: Union[
        GenerationResponse,
        Iterable[GenerationResponse],
    ] = model_client.generate_content(messages)
    candidate: Candidate = model_response.candidates[0]
    if candidate.finish_reason.name != "STOP":
        logger.error(
            f"Model has issue. Candidate finish reason name {candidate.finish_reason.name}. Response: {str(model_response)}"
        )
        return ""
    else:
        return candidate.content.parts[0].text


# Execute image generation request
def get_image_binary(image_list):
    if len(image_list.images) < 1:
        raise AttributeError("GeneratedImage list is empty")
    image = image_list[0]
    if hasattr(image, "_pil_image"):
        buffer = BytesIO()
        # Save the image to the buffer in a specific format (e.g., PNG)
        image._pil_image.save(buffer, format="PNG")
        # Get the binary data from the buffer
        return buffer.getvalue()
    else:
        raise AttributeError(
            "GeneratedImage object does not have a _pil_image attribute"
        )


def do_image_request(prompt: str) -> Union[bytes, None]:

    logger.info("Generating Gemini image with prompt: " + prompt)

    # Load Base 64 encoded key JSON from env variable and convert back to JSON
    credentials: Dict = json.loads(
        base64.b64decode(get_critical_env_variable("GOOGLE_GEMINI_KEY"))
    )
    vertexai.init(
        project=get_critical_env_variable("GOOGLE_GEMINI_PROJECT_ID"),
        location=get_critical_env_variable("GOOGLE_GEMINI_LOCATION"),
        credentials=Credentials.from_service_account_info(credentials),
    )

    generation_model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-001")

    image_list: ImageGenerationResponse = generation_model.generate_images(
        prompt=prompt,
        number_of_images=1,
        aspect_ratio="1:1",
        # safety_filter_level="block_some",
        # user_generation="allow_all",
    )
    return get_image_binary(image_list)
