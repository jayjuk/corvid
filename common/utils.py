from os import environ
import sys

# Graceful exit, specific to AI management cases
def exit(logger, error_message: str) -> None:
    logger.error(error_message + " Exiting.")
    # Write chat_history to file
    with open("exit_chat_history_dump.txt", "w") as f:
        for item in self.chat_history:
            for key, value in item.items():
                f.write(f"{key}: {value}\n")
    sys.exit()

# Check if mandatory environment variable is set
def get_critical_env_variable(env_var_name: str) -> Optional[str]:
    v = environ.get(env_var_name)
    # If it does exist, return it
    if v:
        return environ.get(env_var_name)
    # Otherwise, exit
    exit(f"{env_var_name} not set. Exiting.")