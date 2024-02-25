import os
from logger import setup_logger
from dotenv import load_dotenv
import sys
from azure.core.credentials import AzureNamedKeyCredential
from azure.storage.blob import BlobServiceClient
from flask import Flask, send_from_directory
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions

# Set up logger
logger = setup_logger()


class ImageServer:
    def __init__(self, image_container_name):
        self.app = Flask(__name__)
        # Get Azure storage client
        self.credential = self.get_azure_credential()
        self.blob_service_client = BlobServiceClient(
            account_url="https://"
            + os.environ.get("AZURE_STORAGE_ACCOUNT_NAME")
            + ".blob.core.windows.net",
            credential=self.credential,
        )
        self.cache_folder = image_container_name
        self.image_file_cache = image_container_name
        # Create a local folder named after the container to store images
        os.makedirs(self.image_file_cache, exist_ok=True)

        @self.app.route("/image/<image_name>")
        def get_image(image_name):
            logger.info(f"Request for image {image_name}")
            # Check if the image is in the folder image_container_name
            if not os.path.exists(self.image_file_cache + os.sep + image_name):
                # Download the image from Azure blob storage to the local folder
                logger.info(f"Downloading {image_name} from Azure blob storage")
                blob_client = self.blob_service_client.get_blob_client(
                    image_container_name, image_name
                )
                with open(self.cache_folder + os.sep + image_name, "wb") as f:
                    f.write(blob_client.download_blob().readall())
                    logger.info(f"Cached {image_name} in {self.cache_folder}")

            # Return actual image in the local folder
            return send_from_directory(self.cache_folder, image_name)

    # Utility to check env variable is set
    def check_env_var(self, var_name):
        if not os.environ.get(var_name):
            logger.error(f"{var_name} not set. Exiting.")
            sys.exit(1)

    # Return Azure credential
    # TODO: move to common
    def get_azure_credential(self):
        # TODO: error handling
        if not os.environ.get("AZURE_STORAGE_ACCOUNT_NAME"):
            load_dotenv()
        self.check_env_var("AZURE_STORAGE_ACCOUNT_NAME")
        self.check_env_var("AZURE_STORAGE_ACCOUNT_KEY")
        return AzureNamedKeyCredential(
            os.environ.get("AZURE_STORAGE_ACCOUNT_NAME"),
            os.environ.get("AZURE_STORAGE_ACCOUNT_KEY"),
        )

    def run(self):
        self.app.run(host="0.0.0.0", port=5000)


# Main
if __name__ == "__main__":
    # TODO: move jaysgameimages to env variable
    image_server = ImageServer("jaysgameimages")
    image_server.run()
