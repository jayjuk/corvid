import aimanager

model_name = "gpt-3.5-turbo"  # "gpt-4" #gpt-3.5-turbo-0613
max_tokens = 300
temperature = 0.7

aimanager.create_image("test", "This is a test")

# prompt = "Hi"
# print("Prompt:", prompt)
# response = aimanager.submit_prompt(
#     prompt,
#     model_name=model_name,
#     max_tokens=max_tokens,
#     temperature=temperature,
# )
# print(response)
