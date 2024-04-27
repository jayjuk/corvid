from os import environ
from typing import Optional
import sys


# Check if mandatory environment variable is set
def get_critical_env_variable(env_var_name: str) -> Optional[str]:
    v = environ.get(env_var_name)
    # If it does exist, return it
    if v:
        return environ.get(env_var_name)
    # Otherwise, exit
    print(f"{env_var_name} not set. Exiting.")
    sys.exit(1)
