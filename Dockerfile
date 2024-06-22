# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install build dependencies and common utilities
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc g++ pkg-config build-essential && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy the pyproject.toml and poetry.lock files to the container
COPY pyproject.toml poetry.lock /app/

# Install Poetry
RUN pip install poetry

# Install project dependencies without dev dependencies
RUN poetry install --no-root --only main

# Copy the rest of the application code to the container
COPY . /app

# Expose the port that the app runs on
EXPOSE 8000

# Command to run the FastAPI application using Uvicorn with uvloop
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--loop", "uvloop"]