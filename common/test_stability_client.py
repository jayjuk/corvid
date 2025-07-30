import stability_client
from PIL import Image
from io import BytesIO

def generate_test_image(prompt: str, model_name: str = "stable-diffusion-xl-1024-v1-0"):
    try:
        # Get the model client
        model_client = stability_client.get_model_client(model_name)

        # Generate the image
        image_data = stability_client.do_image_request(prompt)

        if image_data:
            # Save the image
            image = Image.open(BytesIO(image_data))
            output_filename = "test_image.png"
            image.save(output_filename)
            print(f"Image saved as {output_filename}")
            return output_filename
        else:
            print("No image was generated.")
            return None

    except Exception as e:
        print(f"Error generating image: {e}")
        return None

if __name__ == "__main__":
    test_prompt = "A futuristic cityscape at night with neon lights"
    generate_test_image(test_prompt)
