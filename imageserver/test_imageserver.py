import requests

# Make a GET request to the /image/<image_name> endpoint
response = requests.get("http://localhost:5000/image/test.png")

print(response)
# Check if the response is an image file
if response.headers["Content-Type"].startswith("image/"):
    print("The response is an image file.")
else:
    print("The response is not an image file.")
