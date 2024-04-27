import aimanager

model_name = "gpt-3.5-turbo"
max_tokens = 300
temperature = 0.7

ai_manager = aimanager.AIManager("You are a helpful assistant.", model_name=model_name)

while True:
    prompt = input("Prompt:")
    response = ai_manager.submit_request(
        prompt,
        model_name=model_name,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    print(response)
