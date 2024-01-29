FROM python:3.11-slim-bookworm
ADD aibroker/requirements.txt .
ADD aibroker/aibroker.py .
ADD common/logger.py .
RUN pip install -r requirements.txt
CMD ["python", "./aibroker.py"] 
