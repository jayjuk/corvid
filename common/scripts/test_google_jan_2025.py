from google import genai

client = genai.Client(api_key="AIzaSyBCh5q7TpJKz5gCfkUSbk3ieOVZtU3swm4")
response = client.models.generate_content(
    model="gemini-1.5-pro-002", contents="Respond with just the word hi"
)
print(response.text)
