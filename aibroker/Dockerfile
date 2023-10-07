FROM python:3.11-slim-bookworm
ADD aibroker.py .
RUN pip install python-socketio openai
CMD ["python", "./aibroker.py"] 
