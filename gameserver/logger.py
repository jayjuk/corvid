import logging


def setup_logger():
    # Set up logging to file and console
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler("game_server.log"),
            logging.StreamHandler(),
        ],
    )
    logger = logging.getLogger(__name__)
    return logger
