from typing import Union
import os
from utils import get_critical_env_variable, setup_logger


# Set up logger
logger = setup_logger()

# Avoid mixing up loggers by importing third party modules after logger
from stability_sdk import client
import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation


# Get the model client for the specified model
def get_model_client(model_name: str) -> client.StabilityInference:
    os.environ["STABILITY_HOST"] = "grpc.stability.ai:443"
    return client.StabilityInference(
        key=get_critical_env_variable("STABILITY_KEY"),
        verbose=True,
        engine=model_name,
    )


# Execute image generation request
def do_image_request(
    model_client: client.StabilityInference, prompt: str
) -> Union[bytes, None]:

    answers = model_client.generate(
        prompt=prompt,
        steps=50,
        cfg_scale=8.0,
        width=512,
        height=512,
        samples=1,
        sampler=generation.SAMPLER_K_DPMPP_2M,
    )

    for resp in answers:
        for artifact in resp.artifacts:
            if artifact.finish_reason == generation.FILTER:
                logger.warning(
                    "Your request activated the API's safety filters and could not be processed."
                    + " Please modify the prompt and try again."
                )
            if artifact.type == generation.ARTIFACT_IMAGE:
                return artifact.binary
    return None
