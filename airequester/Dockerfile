FROM python:3.11-slim-bookworm
ADD common/requirements.txt ./common_requirements.txt
ADD airequester/requirements.txt ./airequester_requirements.txt
ADD airequester/*.py .
ADD common/*.py .
RUN pip install -r common_requirements.txt && pip install -r airequester_requirements.txt
CMD ["python", "./airequester.py"] 
