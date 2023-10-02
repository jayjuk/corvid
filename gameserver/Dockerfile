FROM python:3.11-slim-bookworm
ADD gameserver.py .
ADD *.json .
RUN pip install python-socketio eventlet
CMD ["python", "./gameserver.py"] 
