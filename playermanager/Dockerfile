FROM python:3.11-slim-bookworm
ADD common/requirements.txt ./common_requirements.txt
ADD aibroker/requirements.txt ./playermanager_requirements.txt
ADD aibroker/*.py .
ADD common/*.py .
RUN pip install -r common_requirements.txt && pip install -r playermanager_requirements.txt
CMD ["python", "./playermanager.py"] 
