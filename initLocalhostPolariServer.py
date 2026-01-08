import os
import sys

# Import configuration loader
from config_loader import config, is_in_docker, get_backend_port

# Check if running in Docker container and adjust Python path
if is_in_docker():
    # If running in a Docker container, add vendor path
    sys.path.insert(0, '/app/vendor')

from objectTreeManagerDecorators import managerObject
from wsgiref.simple_server import make_server
from falcon import falcon

if(__name__=='__main__'):
    #Create a basic manager with a polariServer
    localHostedManagerServer = managerObject(hasServer=True)

    # Get backend port from configuration
    hostport = get_backend_port()

    with make_server('', hostport, localHostedManagerServer.polServer.falconServer) as httpd:
        print(f'Serving on port {hostport}.....')
        print('Access base polari api via link -  http://localhost:' + str(hostport) + '/')
        #Serve on localhost until process is killed.
        httpd.serve_forever()