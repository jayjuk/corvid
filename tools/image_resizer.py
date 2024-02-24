# Loop through a specified directory and resize all images to 512x512
# Usage: python image_resizer.py --input_dir /path/to/input/dir --output_dir /path/to/output/dir
from PIL import Image
import os


def resize_image(input_image_path, output_image_path, size):
    original_image = Image.open(input_image_path)
    width, height = original_image.size
    print(f"The original image size is {width} wide x {height} tall")

    resized_image = original_image.resize(size)
    width, height = resized_image.size
    print(f"The resized image size is {width} wide x {height} tall")
    resized_image.save(output_image_path)


# Main function
def main():
    input_dir = ".\\images\\"
    output_dir = "images_smaller"
    size = (512, 512)

    for filename in os.listdir(input_dir):
        print(filename)
        if filename.endswith(".png"):
            input_image_path = os.path.join(input_dir, filename)
            output_image_path = os.path.join(output_dir, filename)
            resize_image(input_image_path, output_image_path, size)


if __name__ == "__main__":
    main()
