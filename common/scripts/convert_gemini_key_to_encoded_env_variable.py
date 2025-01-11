import base64
import sys

file_name = sys.argv[1] if len(sys.argv) > 1 else "gemini.key"

with open("gemini.key", "rb") as key_file:
    key_data = key_file.read()
    encoded_key = base64.b64encode(key_data)
    with open("gemini_key_encoded.txt", "wb") as encoded_file:
        encoded_file.write(encoded_key)
