import os


# Simple print alternative to flush everything to sdout for now
# TODO: do proper logging using the logging module
def log(message, second_message=""):
    print(str(message) + " " + second_message, flush=True)


def create_folder_if_not_exists(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)


# Make a string safe to be used as a file name
def make_name_safe_for_files(file_name):
    return (
        file_name.replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
        .replace("*", "_")
        .replace("?", "_")
        .replace('"', "_")
        .replace("<", "_")
        .replace(">", "_")
        .replace("|", "_")
    )
