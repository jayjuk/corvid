FROM python:3.11-slim-bookworm
ADD imageserver/requirements.txt .
ADD imageserver/*.py .
ADD common/*.py .
RUN pip install -r requirements.txt
CMD ["python", "./imageserver.py"] 
