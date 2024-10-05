FROM python:3.11-slim-bookworm
ADD common/requirements.txt ./common_requirements.txt
ADD imagecreator/requirements.txt ./imagecreator_requirements.txt
ADD imagecreator/*.py .
ADD common/*.py .
RUN pip install -r common_requirements.txt && pip install -r imagecreator_requirements.txt
CMD ["python", "./imagecreator.py"] 
