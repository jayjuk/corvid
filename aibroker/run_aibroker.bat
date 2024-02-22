set /p OPENAI_API_KEY=<openai.key
set AI_COUNT=1
set AI_MODE=player
@rem set MODEL_NAME=gpt-4-turbo-preview
set MODEL_NAME=gpt-3.5-turbo
@rem set MODEL_NAME=gemini-pro
python aibroker.py %*

