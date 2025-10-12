from typing import Dict, List, Union

from google.cloud import aiplatform
from google.protobuf import json_format
from google.protobuf.struct_pb2 import Value


def predict_custom_trained_model_sample(
    project: str,
    endpoint_id: str,
    credential_dict,
    instances: Union[Dict, List[Dict]],
    location: str = "us-central1",
    api_endpoint: str = "us-central1-aiplatform.googleapis.com",
):
    """
    `instances` can be either single instance of type dict or a list
    of instances.
    """
    # The AI Platform services require regional API endpoints.
    client_options = {"api_endpoint": api_endpoint}
    # Initialize client that will be used to create and send requests.
    # This client only needs to be created once, and can be reused for multiple requests.

    credentials = Credentials.from_service_account_info(credential_dict, scopes=["https://www.googleapis.com/auth/cloud-platform"])

    client = aiplatform.gapic.PredictionServiceClient(client_options=client_options, credentials=credentials)
    # The format of each instance should conform to the deployed model's prediction input schema.
    instances = instances if isinstance(instances, list) else [instances]
    instances = [
        json_format.ParseDict(instance_dict, Value()) for instance_dict in instances
    ]
    parameters_dict = {}
    parameters = json_format.ParseDict(parameters_dict, Value())
    endpoint = client.endpoint_path(
        project=project, location=location, endpoint=endpoint_id
    )
    response = client.predict(
        endpoint=endpoint, instances=instances, parameters=parameters
    )
    print("response")
    print(" deployed_model_id:", response.deployed_model_id)
    # The predictions are a google.protobuf.Value representation of the model's predictions.
    predictions = response.predictions
    for prediction in predictions:
        print(" prediction:", prediction)


# [END aiplatform_predict_custom_trained_model_sample]


import vertexai
from vertexai.preview.generative_models import GenerativeModel
import os
import base64
import json
from google.oauth2.service_account import Credentials


# def get_chat_response(chat, message):
#     response = chat.send_message(message)
#     print(response.text)
#     print("full response:\n", response, "\n\nhistory:", chat.history)


def main():

    project_id = os.environ.get("GOOGLE_GEMINI_PROJECT_ID")
    if not project_id:
        print("ERROR - missing GOOGLE_GEMINI_PROJECT env var")
        exit()

    location = os.environ.get("GOOGLE_GEMINI_LOCATION")
    if not location:
        print("ERROR - missing GOOGLE_GEMINI_LOCATION env var")
        exit()

    gemini_key = os.environ.get("GOOGLE_GEMINI_KEY")
    if not gemini_key:
        print("ERROR - missing GOOGLE_GEMINI_KEY env var")
        exit()

    model_name = "llama-3-1-8b-instruct-1760271127287"#os.environ.get("MODEL_NAME")
    if not model_name:
        print("ERROR - missing MODEL_NAME env var")
        exit()


    print("MODEL_NAME: ", model_name)
    credential_dict = json.loads(base64.b64decode(gemini_key))
    # try:
    #     credential_dict = json.loads(base64.b64decode(gemini_key))

    #     vertexai.init(
    #         project=project_id,
    #         endpoint_id=2025769909828452352,
    #         location=location,
    #         credentials=Credentials.from_service_account_info(credential_dict),
    #     )
    #     model = GenerativeModel(model_name)
    #     chat = model.start_chat(history=[])
    # except Exception as e:
    #     print("ERROR in Gemini startup: ", e)
    #     exit(1)

    #     # user_input = None
    #     # while user_input != "exit":
    #     #     user_input = input("Enter a message: ")
    # #     get_chat_response(chat, user_input)
    # get_chat_response(chat, "Say hi")


    from google.cloud import aiplatform
    from google.protobuf import json_format
    from google.protobuf.struct_pb2 import Value

    endpoint_id = "2025769909828452352"      # your endpoint id

    # Example text-generation style payload used by many MG LLMs (Gemma, Llama, etc.)
    # Check the model card for the exact schema and parameter names.
    params = {"max_tokens": 1024, "temperature": 0.9, "top_p": 1.0, "top_k": 1}
    payload = {"inputs": "Why is the sky blue?", "parameters": params}

    instances = [json_format.ParseDict(payload, Value())]

    #client = aiplatform.gapic.PredictionServiceClient(
    #    credentials=Credentials.from_service_account_info(credential_dict, scopes=["https://www.googleapis.com/auth/cloud-platform"]),
    #    client_options={"api_endpoint": f"{location}-aiplatform.googleapis.com"}
    #)

    #endpoint_path = f"projects/{project_id}/locations/{location}/endpoints/{endpoint_id}"
    print ("So far so good)")
    predict_custom_trained_model_sample(
    project="542912587053",
    endpoint_id="2025769909828452352",
    location="us-central1",
    credential_dict=credential_dict,
    instances={
                "instances": [
                    {
                    "@requestFormat": "chatCompletions",
                    "messages": [
                        {
                            "role": "user",
                            "content": "Hi."
                        }
                    ],
                    "max_tokens": 100
                    }
                ]
            }

)
    #resp = client.predict(endpoint=endpoint_path, instances=instances)
    #print(resp.predictions[0])


if __name__ == "__main__":
    main()
