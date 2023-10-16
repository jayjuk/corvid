FROM python:3.11-slim-bookworm
ADD gameserver/gameserver.py .
ADD gameserver/*.json .
RUN pip install python-socketio eventlet
CMD ["python", "./gameserver.py"] 
