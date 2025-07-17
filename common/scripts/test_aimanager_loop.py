import aimanager
import sys
from utils import set_up_logger

logger = set_up_logger()

# Get model name from command line param
model_name = (
    sys.argv[1] if len(sys.argv) > 1 else "gemini-2.5-flash"  # "llama-3.1-8b-instant"
)

max_tokens = 300
temperature = 0.7

ai_manager = aimanager.AIManager(
    model_name=model_name,
    system_message="You are a helpful assistant. Keep responses to questions concise and brief.",
)
logger.setLevel("WARNING")

while True:
    prompt = input("Prompt:")
    if prompt.lower() in ("exit", "quit", "q", "xox"):
        break
    if prompt.lower() in ("reset", "restart", "clear"):
        ai_manager.reset()
        continue
    if prompt:
        response = ai_manager.submit_request(
            prompt,
            model_name=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        print(response)
