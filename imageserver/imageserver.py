from os import path, environ, makedirs
from logger import setup_logger
from flask import Flask, send_from_directory
from storagemanager import StorageManager

# Set up logger
logger = setup_logger()


class ImageServer:
    def __init__(self):
        self.app = Flask(__name__)
        # Get Azure storage client
        storage_manager = StorageManager(image_only=True)

        self.cache_folder = "image_cache"
        # Create a local folder named after the container to store images
        makedirs(self.cache_folder, exist_ok=True)

        @self.app.route("/image/<image_name>")
        def get_image(image_name):
            logger.info(f"Request for image {image_name}")
            # Check if the image is in the folder image_container_name
            full_image_file_path = path.join(self.cache_folder, image_name)
            if not path.exists(full_image_file_path):
                # Download the image from Azure blob storage to the local folder
                blob = storage_manager.get_image_blob(image_name)
                if blob:
                    with open(full_image_file_path, "wb") as f:
                        f.write(blob)
                        logger.info(f"Cached {image_name} in {self.cache_folder}")

            # Return actual image in the local folder
            return send_from_directory(self.cache_folder, image_name)

    def run(self):
        port = environ["IMAGESERVER_PORT"]
        logger.info(f"Starting up Flask server on port {port}")
        self.app.run(host="0.0.0.0", port=port)


# Main
if __name__ == "__main__":
    logger.info("Starting up Image Server")
    image_server = ImageServer()
    image_server.run()
