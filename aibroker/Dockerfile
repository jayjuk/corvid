FROM python:3.11-slim-bookworm
ADD common/requirements.txt ./common_requirements.txt
ADD aibroker/requirements.txt ./aibroker_requirements.txt
ADD aibroker/aibroker.py .
ADD common/*.py .
RUN pip install -r common_requirements.txt && pip install -r aibroker_requirements.txt
CMD ["python", "./aibroker.py"] 
