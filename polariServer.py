#    Copyright (C) 2020  Dustin Etts
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
from defineLocalSys import *
from objectTreeDecorators import *
from dataStreams import *
from dataChannels import *
from managedFiles import *
import falcon
import subprocess

#Creates a server which either generates an api-endpoint for each object defined in the manager as well as for each dataChannel, or maps them to an endpoint on another server
#which handles that responsibility instead.  The Server can indicate certain polyTypedObjects & dataChannels as 
class polariServer(treeObject):
    @treeObjectInit
    def __init__(self, name, displayName, hostSystem, serverChannel=None, serverDataStream=None):
        self.name = name
        self.displayName = displayName
        self.apiServer = falcon.API()
        self.active = False
        #Defines endpoints or mapping to remote endpoints which allow for CRUD access to all objects of the server's manager as well as it's subordinate manager objects.
        managerIdTuple = self.manager.getInstanceIdentifiers(self.manager)
        self.objectEndpoints = {managerIdTuple:[]}
        #Defines endpoints or mapping to remote endpoints which allow for CRUD access through dataChannel specifications on a server's manager as well as it's subordinate manager objects.
        self.dataChannelEndpoints = {managerIdTuple:[]}
        #A variable used for testing purposes, determines how long the server should be active.
        self.timeActiveInMinutes = 5
        #Records the last time the server on the nodeJS side
        self.lastCycleTime = time.localtime()
        #Sets up the primary data channel which is used as a file relay for information between the back-end and the server
        if(serverChannel == None):
            #print('Setting manager for dataChannel to ', self.manager)
            self.serverChannel = dataChannel(name=name + '_serverChannel', manager=(self.manager))
        else:
            self.serverChannel = serverChannel
        print('ServerChannel: ', self.serverChannel)
        typing = self.manager.getObjectTyping(self.__class__)
        print('Typing Dict for polServer: ')
        #Creates an endpoint for the given manager object for the specific channel object Ex:
        #  https://someURL.com/manager-managerObjectType-(id0:val0, id1:val1, id2:val2, ...)/channel/channelName
        idStr = ((((str( self.manager.getInstanceIdentifiers(self.manager) ).replace(' ','')).replace('(', '')).replace(',', '~')).replace('\'', '')).replace(')','.')
        idStr = idStr[:len(idStr)-3]
        templateURI = '/manager-' + type(self.manager).__name__ + '_' + idStr + '_/channel/' + self.serverChannel.name
        #print('Template URI: ', templateURI)
        self.apiServer.add_route(uri_template = templateURI, resource= polariCRUD(self.serverChannel) )
        self.uriList = [templateURI]
        #The systems that maintain a secure local connection to this system/server and are used
        #for data processing by it, but do not have their own servers.
        self.siblingSystems = []
        #Other servers which maintain a connection with the internet, which this server may
        #maintain APIs to for exclusive access to that server.
        self.siblingServers = []
        #A certificate file which is used to establish and confirm https connections to this server EX: './server.pem'
        self.certFile = None
        #A list of applications (Angular by default) which are being used to establish and serve the frontend of the application.
        self.apps = []
        #A list of data streams / pipelines where the server is constantly sending data to endpoints according to the object's specified conditions.
        self.streams = []
        #Sets the exact system that is the primary host of this server.
        self.setHostSystem(hostSystem)

    def startupPolariServer(self):
        self.serverChannel.makeChannel()
        (self.serverChannel).retrieveDataSet(className=type(self).__name__)
        self.serverChannel.injectJSON()

    def setCertForSSL(self, path, filename):
        if(self.manager != None):
            fileObj = self.manager.makeFile(Path=path, name=filename)

    def polariServerLoop(self):
        self.lastCycleTime = time.localtime()
        #First checks the Main Channel to see if there are any requests there.
        #Note: if the mainChannel is not there, this should not be running.
        now = self.lastCycleTime
        #(Event Loop for the application)
        print('Starting loop at: ' + str(self.lastCycleTime[3]) + ':' + str(self.lastCycleTime[4]))
        while( (now[4] - self.lastCycleTime[4]) < self.timeout):
            now = time.localtime()

    def setHostSystem(self, hostSystemObject=None):
        if(hostSystemObject == None):
            self.hostSystem = isoSys()
        else:
            self.hostSystem = hostSystemObject

    def setMainServerChannel(self):
        self.mainServerChannel

    #THE FOLLOWING FUNCTIONS ARE USED ONLY WHEN SETTING UP A CUSTOM NODE.JS SERVER

    def setupNodeServer(self):
        #Sets up the corresponding javaScript file which defines the server for node.js
        if(sourceFileJS == None and os.path.exists(os.getcwd() + '/managedServer.js')):
            self.sourceFileJS = fileObject(name='managedServer', Path=os.getcwd(), extension='js', manager=self.manager)
        else:
            self.sourceFileJS = sourceFileJS

    def setSourceFile(self, sourceFileJS=None):
        if(sourceFileJS == None):
            sourceFileJS = managedFile()
        else:
            sourceFileJS = sourceFileJS

    def startNodeServer(self):
        #Creates a subprocess for launching the server and navigates directly to the
        #file holding the source code for the Node Express server.
        bytePath = bytes(string, self.sourceFileJS.Path)
        byteName = bytes(string, self.sourceFileJS.name)
        serverProcess = subprocess.Popen(args = b'cd ' + bytePath + b' \n',
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
        #Launches a process with the base code for a Node Express Server.
        serverProcess.stdin.write(b'node ' + byteName + b'.js \n')
        serverProcess.stdin.flush()
        print(serverProcess.stdout.readline())
        #Input data to define the startup of the server and information about the basis of the server
        serverProcess.stdin.write(b'\n')
        serverProcess.stdin.flush()
        print(serverProcess.stdout.readline())
        #Recieve confirmation that the bootup process of the server is completed, start a test information
        #exchange using the server dataChannel.
        serverProcess.stdin.close()
        serverProcess.terminate()
        serverProcess.wait(timeout=0.2)
        output = subprocess.check_output()

#Defines the Create, Read, Update, and Delete Operations for a particular api endpoint designated for a particular dataChannel or polyTypedObject Instance.
class polariCRUD(treeObject):
    
    def __init__(self, apiObject):
        #The polyTypedObject or dataChannel Instance
        self.apiObject = apiObject
        #Records whether the object is a 'polyTypedObject' or a 'dataChannel'
        self.objType = type(apiObject).__name__
        #Defines whether or not the object's home is not accessable on this server and thus must have a re-direct performed to complete the action.
        self.isRemote = self.apiObject.isRemote
        #Ensures the polariCRUD object has a manager that is the same as the manager of it's apiObject.
        self.manager = (self.apiObject).manager

    #Read in CRUD
    async def on_get(self, request, response):
        #Get the authorization data, user data, and potential url parameters, which are both commonly relevant to both cases.
        authSession = request.auth
        authUser = request.context.user
        urlParameters = request.query_string
        if(self.objType == 'polyTypedObject'):
            allVars = self.apiObject.polyTypedVars
        elif(self.objType == 'dataChannel'):
            allObjects = self.apiObject

    async def on_get_collection(self, request, response):
        pass

    #Update in CRUD
    async def on_put(self, request, response):
        authSession = request.auth
        authUser = request.context.user
        urlParameters = request.query_string
        #if(self.objType == 'polyTypedObject'):
            #
        #elif(self.objType == 'dataChannel'):
            #

    async def on_put_collection(self, request, response):
        pass

    #Create in CRUD
    async def on_post(self, request, response):
        authSession = request.auth
        authUser = request.context.user
        urlParameters = request.query_string
        #if(self.objType == 'polyTypedObject'):
            #
        #elif(self.objType == 'dataChannel'):
            #

    async def on_post_collection(self, request, response):
        pass

    #Delete in CRUD
    async def on_delete(self, request, response):
        authSession = request.auth
        authUser = request.context.user
        urlParameters = request.query_string
        #if(self.objType == 'polyTypedObject'):
            #
        #elif(self.objType == 'dataChannel'):
            #

    async def on_delete_collection(self, request, response):
        pass

    #
    def onChannelValidation(apiType):
        #Does the Channel allow for the particular CRUD action to be performed?
        self.apiObject
    #
    def onObjectValidation(apiType):
        #Does the user have 
        self.apiObject

#Defines a class used for basic Cross-origin-resource-sharing (basis taken from sample code on https://falcon.readthedocs.io/en/latest/user/faq.html#faq)
#This allows for the given server to access an API hosted under a different domain name.
class polariCORS:
    def process_response(self, req, resp, resource, req_succeeded):
        resp.set_header('Access-Control-Allow-Origin', '*')
        if (req_succeeded
            and req.method == 'OPTIONS'
            and req.get_header('Access-Control-Request-Method')
        ):
            # NOTE(kgriffs): This is a CORS preflight request. Patch the
            #   response accordingly.
            allow = resp.get_header('Allow')
            resp.delete_header('Allow')
            allow_headers = req.get_header(
                'Access-Control-Request-Headers',
                default='*'
            )
            resp.set_headers((
                ('Access-Control-Allow-Methods', allow),
                ('Access-Control-Allow-Headers', allow_headers),
                ('Access-Control-Max-Age', '86400'),  # 24 hours
            ))