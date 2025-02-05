import vertexai
from vertexai.preview.generative_models import GenerativeModel
import os
import base64
import json
from google.oauth2.service_account import Credentials


def get_chat_response(chat, message):
    response = chat.send_message(message)
    print(response.text)
    print("full response:\n", response, "\n\nhistory:", chat.history)


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

    model_name = os.environ.get("MODEL_NAME")
    if not model_name:
        print("ERROR - missing MODEL_NAME env var")
        exit()

    # Check model name contains gemini
    if "gemini" not in model_name.lower():
        print("ERROR - MODEL_NAME must contain 'gemini'")
        exit()

    print("MODEL_NAME: ", model_name)

    try:
        credential_dict = json.loads(base64.b64decode(gemini_key))

        vertexai.init(
            project=project_id,
            location=location,
            credentials=Credentials.from_service_account_info(credential_dict),
        )
        model = GenerativeModel(model_name)
        chat = model.start_chat(history=[])
    except Exception as e:
        print("ERROR in Gemini startup: ", e)
        exit(1)

        # user_input = None
        # while user_input != "exit":
        #     user_input = input("Enter a message: ")
    #     get_chat_response(chat, user_input)
    get_chat_response(chat, "Say hi")


if __name__ == "__main__":
    main()
