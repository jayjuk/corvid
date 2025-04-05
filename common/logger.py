import logging
import sys
import os
import time
from typing import Any
import signal

# INSTRUCTIONS TO USE THIS MODULE
# At the top of your module, add the following:
# 1. Import it into your module: from utils import set_up_logger
# 2. Set up logging passing in the name of the current file: logger = set_up_logger()
# This will create a log file in the logs directory with the same name as the module (e.g. player.log)
# for unit testing cases, or if the module has been imported from a main file, the parent log file will be used
# (e.g. orchestrator.log)


# Get the logs folder
def get_logs_folder() -> str:
    return "logs"


# Shortest  way to quickly output some content, whatever the mode, easy to then find these statements and remove them later
def debug(*args: Any) -> None:
    """
    This function is used for debugging purposes.
    It takes any number of arguments, prints them, and then sleeps for 1 second.
    """
    debug_content: str = " ".join(str(arg) for arg in args)
    print(f"*** DEBUG: {debug_content} ***")
    sleep_time: int = 1
    print(f"Sleeping {sleep_time} seconds...")
    time.sleep(sleep_time)


# Flag for regular/semipermanent debug logging to be made visible at runtime
def is_debug_mode() -> bool:
    return len(sys.argv) > 1 and sys.argv[1].lower() == "debug"


# Signal handler for SIGINT
def signal_handler(logger, sig, frame):
    logger.info("Signal Interrupt Received - Shutting down...")
    exit(0)


# Register signal handler for SIGINT
def register_signal_handler(logger):
    # signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGINT, lambda sig, frame: signal_handler(logger, sig, frame))


# Function invoked by most modules for shared and common logging
def set_up_logger(
    file_name: str = "unit_testing.log", logging_level_override: str = ""
) -> logging.Logger:
    # If logger already set up, return it
    if logging.getLogger().hasHandlers():
        return logging.getLogger()

    # Otherwise....

    # Append .log to file name if not already there
    if not file_name.endswith(".log"):
        file_name = file_name + ".log"

    # Create logs directory if it doesn't exist
    if not os.path.exists(get_logs_folder()):
        os.makedirs(get_logs_folder())

    # Set logging level based on waterfall of settings
    logging_level: int = logging.INFO
    if is_debug_mode():
        logging_level = logging.DEBUG
    elif logging_level_override:
        logging_level = logging.getLevelName(logging_level_override)
    elif os.environ.get("LOGGER_LOG_LEVEL"):
        logging_level = logging.getLevelName(os.environ.get("LOGGER_LOG_LEVEL"))

    # Set up logging to file and console
    logging.basicConfig(
        level=logging_level,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(os.path.join(get_logs_folder(), file_name)),
            logging.StreamHandler(),
        ],
    )
    register_signal_handler(logging.getLogger())

    return logging.getLogger()


# Default common exit logic which logs a critical error and exits at the same time.
def exit(logger: logging.Logger, error_message: str = None) -> None:
    # If no message, assume normal exit.
    exit_code: int = 0
    if error_message:
        logger.critical(error_message)
        exit_code: int = 1
    else:
        # Check logger not a string
        if isinstance(logger, str):
            print(
                f"I suspect an error message was passed into the logger parameter: {logger}"
            )
    sys.exit(exit_code)
