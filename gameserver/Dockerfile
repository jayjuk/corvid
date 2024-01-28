FROM python:3.11-slim-bookworm
ADD *.py .
ADD *.json .
ADD ../common/logger.py .
ADD requirements.txt .
RUN pip install -r requirements.txt
CMD ["python", "./gameserver.py"] 
