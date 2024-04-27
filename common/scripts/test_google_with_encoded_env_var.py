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

    if not os.environ.get("GEMINI_KEY"):
        print("ERROR - missing GEMINI_KEY env var")
        exit()

    try:
        credential_dict = json.loads(base64.b64decode(os.environ["GEMINI_KEY"]))

        vertexai.init(
            project="jaysgame",
            location="us-central1",
            credentials=Credentials.from_service_account_info(credential_dict),
        )
        model = GenerativeModel("gemini-pro")
        chat = model.start_chat(history=[])
    except Exception as e:
        print("ERROR in Gemini startup: ", e)
        exit(1)

    user_input = None
    while user_input != "exit":
        user_input = input("Enter a message: ")
        get_chat_response(chat, user_input)


if __name__ == "__main__":
    main()
