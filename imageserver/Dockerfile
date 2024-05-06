FROM python:3.11-slim-bookworm
ADD common/requirements.txt ./common_requirements.txt
ADD imageserver/requirements.txt ./imageserver_requirements.txt
ADD imageserver/imageserver.py .
ADD common/*.py .
RUN pip install -r common_requirements.txt && pip install -r imageserver_requirements.txt
CMD ["python", "./imageserver.py"] 
