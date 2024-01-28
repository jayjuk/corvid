FROM python:3.11-slim-bookworm
ADD aibroker.py .
ADD ../common/logger.py .
ADD requirements.txt .
RUN pip install -r requirements.txt
CMD ["python", "./aibroker.py"] 
