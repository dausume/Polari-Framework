# syntax=docker/dockerfile:1

# Comments are provided throughout this file to help you get started.
# If you need more help, visit the Dockerfile reference guide at
# https://docs.docker.com/engine/reference/builder/

FROM python:3.9-alpine

# Set the environment variable indicating whether it's a Docker container
ENV IN_DOCKER_CONTAINER=true

# Prevents Python from writing pyc files.
#ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
#ENV PYTHONUNBUFFERED=1

#ENV PATH="./app"

WORKDIR /app

RUN python -m venv venv

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

# Set environment variables for pip
ENV PIP_DEFAULT_TIMEOUT=60
ENV PIP_RETRY_MAX=5

# Sets the location of the pip cache directory in the container.
# Must be used in the Docker Compose file as well to ensure the mapping
# Used so that you do not have to re-download modules every time 
ENV PIP_CACHE_DIR=/pip-cache/.cache/pip

# Dependency for psutil & freetype, without it they will fail.
RUN apk add gcc g++ python3-dev musl-dev linux-headers freetype-dev make

### START OF FREETYPE FUNCTIONALITY

ENV FREETYPE_VERSION=2.6.1

COPY /freetype/freetype-2.6.1.tar.gz /build/freetype-2.6.1.tar.gz

# The URL for FreeType download - must be manually dragged to freetype folder in polari
# Trying to use wget WILL NOT WORK, it is hosted on a mirror which prevents automated retrieval.
# ENV FREETYPE_MIRROR_URL=https://sourceforge.net/projects/freetype/files/freetype2/2.6.1/freetype-2.6.1.tar.xz/download

# Set the directory for FreeType extraction
ENV FREETYPE_DIR=/build/freetype-2.6.1

# Copy FreeType tar file and extract it
COPY freetype/freetype-2.6.1.tar.gz /tmp/freetype.tar.gz

# Extract the tar file into the specified directory
RUN tar -xf /tmp/freetype.tar.gz -C /build --strip-components=1

RUN rm /tmp/freetype.tar.gz

#RUN mkdir -p $FREETYPE_DIR && \
#    tar -xf /tmp/freetype.tar.gz -C /build/ && \
#    rm /tmp/freetype.tar.gz
# Change the working directory to the FreeType build directory
#WORKDIR $FREETYPE_DIR

# Build FreeType
#RUN ./configure && make && make install

# Set environment variable to point to FreeType build directory
ENV FREETYPE_ROOT=$FREETYPE_DIR

# Set LD_LIBRARY_PATH to include FreeType libraries
ENV LD_LIBRARY_PATH="$FREETYPE_DIR/builds/unix/:$LD_LIBRARY_PATH"

### END OF FREETYPE FUNCTIONALITY

# Copy requirements file
COPY requirements.txt /app/requirements.txt

# Install requirements

RUN pip install -r /app/requirements.txt

RUN pip install psutil

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
# simply enter 'exit' to exit the container terminal to return to host.
#CMD ["sleep", "infinity"]
# Run the application.
CMD ["python3", "initLocalhostPolariServer.py"]
# Used for debugging
#CMD ["tail", "-f", "/dev/null"]