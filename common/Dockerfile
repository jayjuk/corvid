FROM python:3.11-slim-bookworm

# Define a build argument for the specific directory / name (must match)
ARG SERVICE_NAME

# Copy only the requirements files first to leverage Docker cache
COPY common/requirements.txt ./common_requirements.txt
COPY ${SERVICE_NAME}/requirements.txt ./specific_requirements.txt

# Install the dependencies
RUN pip install --no-cache-dir -r common_requirements.txt && \
    pip install --no-cache-dir -r specific_requirements.txt

# Copy the rest of the application code
COPY ${SERVICE_NAME}/*.py .
COPY ${SERVICE_NAME}/*_data .
COPY common/*.py .

# Create a copy of the main module named main, to use a common Dockerfile
# TODO #106 Find a way to use a common Dockerfile without copying the main module file
COPY ${SERVICE_NAME}/${SERVICE_NAME}.py main.py
# Set the default command
CMD ["python", "./main.py"]
