# syntax=docker/dockerfile:1
#
# Dockerfile for building and running the Python application.
# It uses a multi-stage build to create wheel files for dependencies
# in a full Python environment, then installs them in a slim Python image
# to reduce the final image size.
#
# Stage 1: Build wheels for dependencies
FROM python:3.12 AS wheel

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file to the working directory
COPY requirements.txt .

# Install wheel package and build wheel files for all dependencies listed in requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install wheel && \
    pip wheel --exists-action i -r requirements.txt --wheel-dir /root/.cache/wheel

# Stage 2: Create the final image with a slim Python base
FROM python:3.12-slim

# Environment variable to indicate running inside Docker
ENV IN_DOCKER=1

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file to the working directory
COPY requirements.txt .

# Install dependencies from the pre-built wheel files from the previous stage
RUN --mount=type=bind,from=wheel,source=/root/.cache/wheel,dst=/root/.cache/wheel \
    pip install --no-index --find-links=/root/.cache/wheel -r requirements.txt

# Copy the entire application code into the container
COPY . .

# Copy the entrypoint script and set executable permissions
COPY --chmod=777 docker/entrypoint.sh /

# Set the entrypoint for the container
ENTRYPOINT [ "/entrypoint.sh" ]
