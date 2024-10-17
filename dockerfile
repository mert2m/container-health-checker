# Use a stable Python base image
FROM python:3.9-slim

# Add label for authorship
LABEL authors="mertpolat"

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install the docker Python package
RUN pip install --no-cache-dir docker

# Run the monitor script
CMD ["python", "main.py"]
