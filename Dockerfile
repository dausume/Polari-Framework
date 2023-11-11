# syntax=docker/dockerfile:1

# Comments are provided throughout this file to help you get started.
# If you need more help, visit the Dockerfile reference guide at
# https://docs.docker.com/engine/reference/builder/

ARG PYTHON_VERSION=3.9
FROM python:${PYTHON_VERSION}-buster as base

# Set the environment variable indicating whether it's a Docker container
ENV IN_DOCKER_CONTAINER=true

# Prevents Python from writing pyc files.
#ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
#ENV PYTHONUNBUFFERED=1

#ENV PATH="./app"

WORKDIR /app

# Create a non-privileged user that the app will run under.
# See https://docs.docker.com/go/dockerfile-user-best-practices/
#ARG UID=10001
#RUN adduser \
#    --disabled-password \
#    --gecos "" \
#    --home "/nonexistent" \
#    --shell "/sbin/nologin" \
#    --no-create-home \
#   --uid "${UID}" \
#    appuser

# Download dependencies as a separate step to take advantage of Docker's caching.
# Leverage a cache mount to /root/.cache/pip to speed up subsequent builds.
# Leverage a bind mount to requirements.txt to avoid having to copy them into
# into this layer.
#RUN --mount=type=cache,target=/root/.cache/pip \
#    --mount=type=bind,source=requirements.txt,target=requirements.txt \
#    python -m pip install --no-cache-dir --index-url https://pypi.org/simple/ -r requirements.txt

COPY requirements.txt .

RUN python3 -m pip install --no-cache-dir --index-url https://pypi.org/simple/ -r requirements.txt --target /app/vendor

# Switch to the non-privileged user to run the application.
#USER appuser

# Copy the source code into the container.
COPY . /app

#RUN chmod +x /app/initLocalHostPolariServer.py

# Set default environment variables
ENV PORT 3000
ENV DEPLOY_ENV development

# Expose the port that the application listens on.
EXPOSE $PORT

#Uncomment line if you have trouble getting docker image to build and need to debug
#After running can open secure shell to inspect what is wrong using command below
#docker exec -it container_name_or_id /bin/bash
#CMD ["sleep", "infinity"]

# Run the application.
CMD ["/usr/bin/python3", "/app/initLocalhostPolariServer.py"]