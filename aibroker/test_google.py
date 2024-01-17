from google.cloud import aiplatform_v1
import vertexai
from vertexai.preview.generative_models import GenerativeModel
import os

# If env variable not set and file exists, set it
# set GOOGLE_APPLICATION_CREDENTIALS=
gcloud_credentials_file = "gemini.key"
if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
    if not os.path.exists(gcloud_credentials_file):
        print(
            "GOOGLE_APPLICATION_CREDENTIALS not set and {} does not exist".format(
                gcloud_credentials_file
            )
        )
        exit()
    else:
        print(
            "Setting GOOGLE_APPLICATION_CREDENTIALS to {}".format(
                gcloud_credentials_file
            )
        )
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = gcloud_credentials_file


vertexai.init(project="jaysgame", location="us-central1")
model = GenerativeModel("gemini-pro")
chat = model.start_chat(history=[])


def get_chat_response(chat, message):
    response = chat.send_message(message)
    print(response.text)
    print("full response:\n", response, "\n\nhistory:", chat.history)


user_input = None
while user_input != "exit":
    user_input = input("Enter a message: ")
    get_chat_response(chat, user_input)
