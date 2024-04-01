import aimanager

aimanager.logger
model_name = "gemini-pro"
max_tokens = 300
temperature = 0.3

ai_manager = aimanager.AIManager("...", model_name=model_name)

while True:
    prompt = input("Prompt:")
    response = ai_manager.submit_request(
        prompt,
        model_name=model_name,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    print(response)
