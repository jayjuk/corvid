import logging
import os


def setup_logger(file_name):
    # Create logs directory if it doesn't exist
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    # Set up logging to file and console
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(logs_dir + os.sep + file_name),
            logging.StreamHandler(),
        ],
    )
    logger = logging.getLogger(__name__)
    return logger
