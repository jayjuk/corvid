while True:
    user_input = input("Enter a string (or type 'exit' to quit): ")
    if user_input.lower() == 'exit':
        break

    # Increment each character's ASCII value by 1
    modified_string = ''.join(chr(ord(char) + 1) for char in user_input)

    print("Modified string:", modified_string)


