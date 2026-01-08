# Dev - Building Polari Backend in isolation
Look in the build-commands.md files of polari-framework and polari-framework for
the isolation-dev build commands.  You will only need to declare the polari-node
network once for the overall app.

Command for making the polari-node network (remove sudo if in non-linux environment):

    sudo docker network create polari-node-network

To create/build the polari backend in isolation:

    docker-compose -f docker-compose.yml build

To spin up the polari backend in isolation:

    docker-compose -f docker-compose.yml up -d