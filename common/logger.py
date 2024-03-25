import logging
import sys
import os
import time

# INSTRUCTIONS TO USE THIS MODULE
# At the top of your module, add the following:
# 1. Import it into your module: from logger import setup_logger
# 2. Set up logging passing in the name of the current file: logger = setup_logger()
# This will create a log file in the logs directory with the same name as the module (e.g. player.log)
# for unit testing cases, or if the module has been imported from a main file, the parent log file will be used
# (e.g. gameserver.log)


# Shortest  way to quickly output some content, whatever the mode, easy to then find these statements and remove them later
def debug(
    debug_content,
    debug_content2="",
    debug_content3="",
):
    print(f"*** DEBUG: {debug_content} {debug_content2} {debug_content3} ***")
    sleep_time = 1
    print(f"Sleeping {sleep_time} seconds...")
    time.sleep(sleep_time)


# Flag for regular/semipermanent debug logging to be made visible at runtime
def is_debug_mode():
    return len(sys.argv) > 1 and sys.argv[1].lower() == "debug"


# Function invoked by most modules for shared and common logging
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


# Default common exit logic which logs a critical error and exits at the same time.
def exit(logger, error_message=None):
    if error_message:
        logger.critical(error_message)
        exit_code = 1
    else:
        # Check logger not a string
        if isinstance(logger, str):
            print(
                f"I suspect an error message was passed into the logger parameter: {logger}"
            )
        # If no message, assume normal exit.
        exit_code = 0
    sys.exit(exit_code)
