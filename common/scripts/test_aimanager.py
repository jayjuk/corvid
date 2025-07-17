import aimanager

model_name = "gemini-2.5-flash"  # Other models: gemini-2.0-flash gpt-4o-mini
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
print(response)
