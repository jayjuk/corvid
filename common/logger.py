import logging
import sys
import os

# INSTRUCTIONS TO USE THIS MODULE
# At the top of your module, add the following:
# 1. Import it into your module: from logger import setup_logger
# 2. Set up logging passing in the name of the current file: logger = setup_logger()
# This will create a log file in the logs directory with the same name as the module (e.g. player.log)
# for unit testing cases, or if the module has been imported from a main file, the parent log file will be used
# (e.g. gameserver.log)


def is_debug_mode():
    return len(sys.argv) > 1 and sys.argv[1].lower() == "debug"


def setup_logger(file_name="unit_testing.log"):
    # If logger already set up, return it
    if logging.getLogger().hasHandlers():
        return logging.getLogger()

    # Otherwise....

    # Append .log to file name if not already there
    if not file_name.endswith(".log"):
        file_name = file_name + ".log"

    # Create logs directory if it doesn't exist
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    if is_debug_mode():
        logging_level = logging.DEBUG
    else:
        logging_level = logging.INFO

    # Set up logging to file and console
    logging.basicConfig(
        level=logging_level,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(logs_dir + os.sep + file_name),
            logging.StreamHandler(),
        ],
    )
    logger = logging.getLogger()
    return logger
