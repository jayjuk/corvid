import os
import google.generativeai as genai

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Create the model
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
}

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config=generation_config,
)

chat_session = model.start_chat(
    history=[
        {
            "role": "user",
            "parts": [
                "testing",
            ],
        },
        {
            "role": "model",
            "parts": [
                "Okay, I'm ready for your test. What would you like me to do or answer?\n",
            ],
        },
    ]
)

response = chat_session.send_message("is this thing on?")

print(response.text)
