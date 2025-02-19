from os import path, environ, makedirs
from typing import Optional, Union
from flask import Flask, send_from_directory, Response
from azurestoragemanager import AzureStorageManager
from storagemanager import StorageManager
from utils import get_critical_env_variable, setup_logger

# Set up logger
logger = setup_logger("Image Server")


class ImageServer:

    # Constructor allows for either Azure or local storage manager (the latter for unit tests)
    def __init__(
        self, storage_manager: Union[StorageManager, AzureStorageManager] = None
    ) -> None:
        self.app: Flask = Flask(__name__)

        # Get Azure storage client or use one passed in
        self.storage_manager: Union[StorageManager, AzureStorageManager]
        if storage_manager:
            self.storage_manager = storage_manager
        else:
            self.storage_manager = StorageManager(image_only=True)

        self.cache_folder: str = "image_cache"
        # Create a local folder named after the container to store images
        makedirs(self.cache_folder, exist_ok=True)

        @self.app.route("/image/<blob_name>")
        def get_image(blob_name: str) -> Optional[Response]:
            return self.do_get_image(blob_name)

    def run(self) -> None:
        port: str = get_critical_env_variable("IMAGESERVER_PORT")
        logger.info(f"Starting up Flask server on port {port}")
        self.app.run(host="0.0.0.0", port=port)

    def do_get_image(self, blob_name: str) -> Optional[Response]:
        logger.info(f"Request for image {blob_name}")
        # Check if the image is in the folder image_container_name
        full_image_file_path: str = path.join(self.cache_folder, blob_name)
        if not path.exists(full_image_file_path):
            # Download the image from Azure blob storage to the local folder
            blob = self.storage_manager.get_image_blob(blob_name)
            if blob:
                with open(full_image_file_path, "wb") as f:
                    f.write(blob)
                    logger.info(f"Cached {blob_name} in {self.cache_folder}")
            else:
                return None

        # Return actual image in the local folder
        return send_from_directory(self.cache_folder, blob_name)


# Main - start the image server with real Azure storage
if __name__ == "__main__":
    logger.info("Starting up Image Server")
    storage_manager: AzureStorageManager = AzureStorageManager(image_only=True)
    image_server: ImageServer = ImageServer(storage_manager)
    image_server.run()
