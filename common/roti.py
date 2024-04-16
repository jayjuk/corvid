import string

def rot13(text):
    # Define the translation table: rotate the alphabet by 13 places
    rot13_translation = str.maketrans(
        string.ascii_uppercase + string.ascii_lowercase,
        string.ascii_uppercase[13:] + string.ascii_uppercase[:13] +
        string.ascii_lowercase[13:] + string.ascii_lowercase[:13]
    )
    # Translate the text using the ROT13 translation table
    return text.translate(rot13_translation)

while True:
    user_input = input("Enter text to encode/decode (type 'exit' to quit): ")
    if user_input.lower() == 'exit':
        break
    print("Result:", rot13(user_input))


