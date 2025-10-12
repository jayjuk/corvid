import os
from dotenv import load_dotenv
load_dotenv("../.env", override=True)
import aimanager
import sys

model_name = sys.argv[1] if len(sys.argv) > 1 else "openai/gpt-5-mini"#"gpt-4o-mini"# "publishers/google/models/gemini-2.5-flash" #"publishers/anthropic/models/claude-sonnet-4" # "publishers/meta/models/llama-4-maverick-17b-128e-instruct-maas" #"publishers/deepseek-ai/models/deepseek-v3.1-maas"  # Other models: gemini-2.5-flash gemini-2.0-flash gpt-4o-mini
max_tokens = 300
temperature = 0.7

ai_manager = aimanager.AIManager(
    model_name=model_name, system_message="You are a helpful assistant."
)

# ai_manager.create_image("test", "This is a test")

prompt = "Hi"
print("Prompt:", prompt)
response = ai_manager.submit_request(
    prompt,
    model_name=model_name,
    max_tokens=max_tokens,
    temperature=temperature,
)
