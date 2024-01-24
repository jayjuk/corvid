import logging


def setup_logger(file_name="game_server.log"):
    # Set up logging to file and console
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(file_name),
            logging.StreamHandler(),
        ],
    )
    logger = logging.getLogger(__name__)
    return logger
