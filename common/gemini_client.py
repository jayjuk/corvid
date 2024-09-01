from logger import setup_logger
import os
from typing import List, Dict, Union, Iterable
import json
import base64
from typing import Optional
from utils import get_critical_env_variable

# Set up logger
logger = setup_logger()

# Avoid mixing up loggers by importing third party modules after logger
import vertexai
from vertexai.preview.generative_models import (
    GenerativeModel,
    GenerationResponse,
    Content,
    Part,
    Candidate,
)
from google.oauth2.service_account import Credentials
from google.cloud.aiplatform_v1beta1.types.content import SafetySetting
from vertexai.preview.generative_models import HarmCategory, HarmBlockThreshold


# Connect to the LLM API
def get_model_client() -> GenerativeModel:

    # Load Base 64 encoded key JSON from env variable and convert back to JSON
    credentials: Dict = json.loads(
        base64.b64decode(get_critical_env_variable("GOOGLE_GEMINI_KEY"))
    )

    vertexai.init(
        project="jaysgame",
        location="us-central1",
        # This overrides the default use of GOOGLE_APPLICATION_CREDENTIALS containing a file with the key in JSON
        credentials=Credentials.from_service_account_info(credentials),
    )

    safety_settings: Optional[List[SafetySetting]] = None

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
    return GenerativeModel("gemini-pro", safety_settings=safety_settings)


# Build a message for the model
def build_message(role: str, content: str) -> Union[Dict[str, str], Content]:
    return Content(role=role, parts=[Part.from_text(content)])


# Get the model response (Gemini specific)
def do_request(model_client: GenerativeModel, messages: List[Dict[str, str]]) -> str:
    model_response: Union[
        GenerationResponse,
        Iterable[GenerationResponse],
    ] = model_client.generate_content(messages)
    candidate: Candidate = model_response.candidates[0]
    if candidate.finish_reason.name != "STOP":
        logger.error(f"Model has issue: {str(model_response)}")
    else:
        return candidate.content.parts[0].text
    return ""
