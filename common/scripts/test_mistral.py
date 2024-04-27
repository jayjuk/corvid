from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage
import os
from pprint import pprint


key_file = "mistral.key"
if not os.environ.get("MISTRAL_API_KEY"):
    if not os.path.exists(key_file):
        print(f"MISTRAL_API_KEY not set and {key_file} does not exist")
        exit()
    else:
        # read key from file
        os.environ["MISTRAL_API_KEY"] = open(key_file).read().strip()

api_key = os.environ["MISTRAL_API_KEY"]
model = "mistral-tiny"

client = MistralClient(api_key=api_key)

# messages = [ChatMessage(role="user", content="Hi")]

messages = []

while True:
    user_input = input("\nYou: ")
    if user_input == "exit":
        break
    messages.append(ChatMessage(role="user", content=user_input))
    # No streaming
    chat_response = client.chat(
        model=model,
        messages=messages,
    )
    response_text = chat_response.choices[0].message.content.replace("\n\n", "\n")
    print("\nMistral:", response_text)
    messages.append(ChatMessage(role="assistant", content=response_text))

# With streaming
# output = ""
# for chunk in client.chat_stream(model=model, messages=messages):
#     x = chunk.choices[0].delta.content
#     if x:
#         output += x
# print(output)
