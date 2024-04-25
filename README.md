# Polari-Framework
A prototype system meant to facilitate Open Source research and allowing people to easily combine multiple existing open source solutions in python and combine them in single node which can automatically create both a database in sqlite and a server using falcon for all desired objects.

### Running the Polari Backend App in isolation
The easiest way to run the app in most any situation is going to be using Docker Compose.
To run this app by itself (independently build just the backend), you will first need to install docker.

Before trying to run the app make sure the Docker Engine (Docker Daemon) is running.

On windows this may be done most easily using Docker Desktop, starting the Docker Desktop app can start the Engine.

After installing Docker and making sure the enginer is running, go into the termianl and navigate to the working directory of the polari backend app and run the following two commands.

# Builds the app - takes a few mins
Docker compose build

# Runs the app - may take a minute before it starts up
Docker compose up

This will run it using the default settings