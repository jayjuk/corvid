import os

from groq import Groq

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)

while True:
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": input("Input question: "),
            }
        ],
        model="llama-3.1-8b-instant",
    )

    print(chat_completion.choices[0].message.content)
