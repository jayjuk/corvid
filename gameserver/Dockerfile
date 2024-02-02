FROM python:3.11-slim-bookworm
ADD gameserver/requirements.txt .
ADD gameserver/*.py .
ADD gameserver/*.json .
ADD common/*.py .
RUN pip install -r requirements.txt
CMD ["python", "./gameserver.py"] 
