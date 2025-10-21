from dotenv import load_dotenv

# Load environment variables from ../common/.env
load_dotenv("../.env", override=True)

# import os
# from dotenv import load_dotenv
# load_dotenv("../.env", override=True)
# import aimanager
# import sys

# model_name = sys.argv[1] if len(sys.argv) > 1 else "openai/gpt-5-mini"#"gpt-4o-mini"# "publishers/google/models/gemini-2.5-flash" #"publishers/anthropic/models/claude-sonnet-4" # "publishers/meta/models/llama-4-maverick-17b-128e-instruct-maas" #"publishers/deepseek-ai/models/deepseek-v3.1-maas"  # Other models: gemini-2.5-flash gemini-2.0-flash gpt-4o-mini
# max_tokens = 300
# temperature = 0.7

# ai_manager = aimanager.AIManager(
#     model_name=model_name, system_message="You are a helpful assistant."
# )

# # ai_manager.create_image("test", "This is a test")

# prompt = "Hi"
# print("Prompt:", prompt)
# response = ai_manager.submit_request(
#     prompt,
#     model_name=model_name,
#     max_tokens=max_tokens,
#     temperature=temperature,
# )


from openai import OpenAI
import os

client = OpenAI(  
  base_url = "https://oacorvid.openai.azure.com/openai/v1/",  
  api_key=os.environ["OPENAI_API_KEY"]
,
)

response = client.responses.create(
    model="gpt-4o-mini",
    input= "Say just hi back" 
)

print(response.output[0].content[0].text) 



# import os
# import base64
# from openai import AzureOpenAI

# endpoint = os.getenv("AZURE_OPENAI_BASE_URL", "https://oacorvid.openai.azure.com/openai/v1/")
# deployment = os.getenv("DEPLOYMENT_NAME", "gpt-4o-mini")
# subscription_key = os.getenv("AZURE_OPENAI_API_KEY", "REPLACE_WITH_YOUR_KEY_VALUE_HERE")
# print(subscription_key)
# # Initialize Azure OpenAI client with key-based authentication
# client = AzureOpenAI(
#     azure_endpoint=endpoint,
#     api_key=subscription_key,
#     api_version="2025-01-01-preview",
# )

# # IMAGE_PATH = "YOUR_IMAGE_PATH"
# # encoded_image = base64.b64encode(open(IMAGE_PATH, 'rb').read()).decode('ascii')

# # Prepare the chat prompt
# chat_prompt = [
#     {
#         "role": "system",
#         "content": [
#             {
#                 "type": "text",
#                 "text": "You are an AI assistant that helps people find information."
#             }
#         ]
#     },
#     {
#         "role": "user",
#         "content": [
#             {
#                 "type": "text",
#                 "text": "say hi"
#             }
#         ]
#     },
#     {
#         "role": "assistant",
#         "content": [
#             {
#                 "type": "text",
#                 "text": "Hi there! How can I assist you today?"
#             }
#         ]
#     }
# ]

# # Include speech result if speech is enabled
# messages = chat_prompt

# # Generate the completion
# completion = client.chat.completions.create(
#     model=deployment,
#     input="Say just hi",
#     #messages=messages,
#     max_tokens=6553,
#     temperature=0.7,
#     top_p=0.95,
#     frequency_penalty=0,
#     presence_penalty=0,
#     stop=None,
#     stream=False
# )

# print(completion.to_json())
    
