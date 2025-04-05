FROM python:3.11-slim-bookworm
ADD common/requirements.txt ./common_requirements.txt
ADD aibroker/requirements.txt ./agentmanager_requirements.txt
ADD aibroker/*.py .
ADD common/*.py .
RUN pip install -r common_requirements.txt && pip install -r agentmanager_requirements.txt
CMD ["python", "./agentmanager.py"] 
