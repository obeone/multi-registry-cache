# syntax=docker/dockerfile:1

# Start the build stage for creating wheels
FROM python:3.12 AS wheel

# Set the working directory
WORKDIR /app

# Copy the requirements file to the working directory
COPY requirements.txt .

# Install wheel and create wheel files for the requirements
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install wheel && \
    pip wheel --exists-action i -r requirements.txt --wheel-dir /root/.cache/wheel

# Start the final image using a slimmer version of Python
FROM python:3.12-slim

ENV IN_DOCKER=1

# Set the working directory
WORKDIR /app

# Copy the requirements file to the working directory
COPY requirements.txt .

# Install the dependencies from the wheel files created in the previous stage
RUN --mount=type=bind,from=wheel,source=/root/.cache/wheel,dst=/root/.cache/wheel \
    pip install --no-index --find-links=/root/.cache/wheel -r requirements.txt

# Copy the entire application code to the working directory
COPY . .

# Copy the entrypoint script and set the appropriate permissions
COPY --chmod=777 docker/entrypoint.sh /

# Specify the entrypoint for the container
ENTRYPOINT [ "/entrypoint.sh" ]
