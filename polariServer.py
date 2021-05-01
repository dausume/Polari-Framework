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
from polariCORS import polariCORS
from polariCRUD import polariCRUD
import falcon
import subprocess

#Creates a server which either generates an api-endpoint for each object defined in the manager as well as for each dataChannel, or maps them to an endpoint on another server
#which handles that responsibility instead.  The Server can indicate certain polyTypedObjects & dataChannels as 
class polariServer(treeObject):
    @treeObjectInit
    def __init__(self, name="NEW_SERVER", displayName="NEW_POLARI_SERVER", hostSystem=None, serverChannel=None, serverDataStream=None):
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
        self.apiServer.add_route(uri_template = templateURI, resource= polariCRUD(self.serverChannel, manager=self.manager) )
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

    def setMainServerChannel(self):
        self.mainServerChannel

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