import openai
import os
from dotenv import load_dotenv
from pprint import pprint


def query_gpt(model_client, prompt):
    system_message = (
        "You are a helpful AI assistant focused on helping your user to find a job."
    )
    messages = [
        {
            "role": "system",
            "content": system_message,
        }
    ]
    messages.append(
        {
            "role": "user",
            "content": prompt,
        }
    )
    response = model_client.chat.completions.create(
        model="gpt-4-0125-preview",
        messages=messages,
        max_tokens=500,
    )
    # Extract response content
    for choice in response.choices:
        return choice.message.content


def main():
    load_dotenv()
    openai.api_key = os.getenv("OPENAI_API_KEY")
    model_client = openai.OpenAI()

    while True:
        user_prompt = input("Enter your prompt (or 'quit' to exit): ")
        if user_prompt.lower() == "quit":
            break
        if user_prompt == "":
            print("Prompt cannot be empty!")
            continue

        response_text = query_gpt(model_client, user_prompt)
        print("AI response:", response_text)


if __name__ == "__main__":
    main()
