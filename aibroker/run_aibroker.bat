set /p OPENAI_API_KEY=<openai.key
set AI_COUNT=1
set AI_MODE=player

xcopy /D /Y ..\common\logger.py .\

python aibroker.py
