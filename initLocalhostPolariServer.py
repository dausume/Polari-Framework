from objectTreeManagerDecorators import managerObject
from wsgiref.simple_server import make_server
from falcon import falcon

if(__name__=='__main__'):
    #Create a basic manager with a polariServer
    localHostedManagerServer = managerObject(hasServer=True)
    hostport = 3000
    with make_server('', hostport, localHostedManagerServer.polServer.falconServer) as httpd:
        print('Serving on port 3000.....')
        print('Access base polari api via link -  http://localhost:' + str(hostport) + '/')
        #Serve on localhost until process is killed.
        httpd.serve_forever()