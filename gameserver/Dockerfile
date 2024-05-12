FROM python:3.11-slim-bookworm
ADD common/requirements.txt ./common_requirements.txt
ADD gameserver/requirements.txt ./gameserver_requirements.txt
ADD gameserver/*.py .
COPY gameserver/world_data ./world_data
ADD common/*.py .
RUN pip install -r common_requirements.txt && pip install -r gameserver_requirements.txt
CMD ["python", "./gameserver.py"] 
