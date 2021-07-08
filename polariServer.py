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
from polariAPI import polariAPI
from polariPermissionSet import polariPermissionSet
from polariUserGroupings import UserGroup
from wsgiref import simple_server
import falcon
import subprocess

class apiError(Exception):
    @staticmethod
    async def handle(ex, req, resp, params):
        # TODO: Log the error, clean up, etc. before raising
        raise falcon.HTTPInternalServerError()

#Creates a server which either generates an api-endpoint for each object defined in the manager as well as for each dataChannel, or maps them to an endpoint on another server
#which handles that responsibility instead.  The Server can indicate certain polyTypedObjects & dataChannels as 
class polariServer(treeObject):
    @treeObjectInit
    def __init__(self, name="NEW_SERVER", displayName="NEW_POLARI_SERVER", hostSystem=None, serverChannel=None, serverDataStream=None):
        self.name = name
        self.displayName = displayName
        self.falconServer = falcon.API()
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
        #if(serverChannel == None):
            #print('Setting manager for dataChannel to ', self.manager)
        #    self.serverChannel = dataChannel(name=name + '_serverChannel', manager=(self.manager))
        #else:
        #    self.serverChannel = serverChannel
        #print('ServerChannel: ', self.serverChannel)
        typing = self.manager.getObjectTyping(self.__class__)
        print('Typing Dict for polServer: ')
        #Get the typing for the manager object which houses this server.
        managerType = type(self.manager).__name__
        #SECURE: Does not grant any visibility by default.
        self.secureManagerObjects = []
        #PROTECTED: Grants only read by default.
        self.protectedManagerObjects = [managerType]
        #PUBLIC: Anyone with access to read all and create by default.
        #anything which someone has created will be granted modify access by default.
        #Secondary permissions grant update based on creators or other criteria.
        self.publicManagersList = []
        self.apiRestrictedObjects = ["isoSys"]
        self.secureTreeObjects = []
        self.protectedTreeObjects = ["polyTypedObject", "polyTypedVar", "polariServer", "managedDatabase"]
        self.publicTreeObjectsList = []
        #Creates an endpoint for the given manager object for the specific channel object Ex:
        #  https://someURL.com/manager-managerObjectType-(id0:val0, id1:val1, id2:val2, ...)/channel/channelName
        idStr = ((((str( self.manager.getInstanceIdentifiers(self.manager) ).replace(' ','')).replace('(', '')).replace(',', '~')).replace('\'', '')).replace(')','.')
        idStr = idStr[:len(idStr)-3]
        self.serverManagerURI = '/manager/' + 'managerType=' + type(self.manager).__name__ +'&managerIdTuple=' + idStr + '/'
        self.serverTouchPointAPI = polariAPI(apiName='', availableObjectsList=[self], manager=self.manager)
        self.falconServer.add_route('/'+self.serverTouchPointAPI.apiName, self.serverTouchPointAPI)
        #mainChannelURI = self.baseURIprefix + 'channel/' + self.serverChannel.name + '/' + self.baseURIpostfix
        #print('Template URI: ', templateURI)
        self.crudObjectsList = []
        #self.crudObjectsList.append(polariCRUD(self.serverChannel, manager=self.manager))
        #self.apiServer.add_route(uri_template = mainChannelURI, resource= self.crudObjectsList[0] )
        self.uriList = []
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
        #
        self.groups = []
        #
        self.serverInstance = None

    #Creates a new sink which operates stictly over a secure local network (Wifi Router)
    def makeNewLocalSink(self, localNetworkedSystemIP, remotePort, managerAPI):
        #Set up a new sink instance in order to proxy things to another service
        sink = SinkAdapter()
        sinkURL = '/' + localNetworkedSystemIP + '/' + remotePort + '/' + managerAPI
        app.add_sink(sink, sinkURL.encode('unicode_escape'))

    def makeNewErrorType(self):
        # If a responder ever raises an instance of StorageError, pass control to
        # the given handler.
        app.add_error_handler(apiError, apiError.handle)

    def startLocalServerRun(self):
        self.serverInstance = simple_server.make_server('127.0.0.1', 8000, self.apiServer)
        self.serverInstance.serve_forever()

    def makeDefaultUserGroups(self):
        #Make AdminGroup access group - users with admin privilages.
        self.groups.append(UserGroup(groupname="AdminGroup", manager=self.manager))
        #Make SecureLocalSystems access group - for connected systems on a secure network.
        self.groups.append(UserGroup(groupname="SecureLocalSystems", manager=self.manager))
        #Make RemoteConnectedSystems access group - for connected systems which communicate over the internet.
        self.groups.append(UserGroup(groupname="RemoteConnectedSystems", manager=self.manager))
        #Make AuthenticatedUsers access group - for users that have logged in and been authenticated.
        self.groups.append(UserGroup(groupname="AuthenticatedUsers", manager=self.manager))
        #Make AnonymousTrackedUsers access group - for users who have yet to log in or are browsing anonymously.
        self.groups.append(UserGroup(groupname="AnonymousTrackedUsers", manager=self.manager))
        #Make PotentialSecurityThreat access group - for anonymous users who have triggered multiple security flags and may be trying to infiltrate the system.
        #(this can be used to prevent many attempts from singular IPs at accessing the Node)
        self.groups.append(UserGroup(groupname="PotentialSecurityThreat", manager=self.manager))
        return

    #This can be run to quickly produce permission sets which allow access to everything
    #SHOULD ONLY EVER BE RUN WHILE TESTING ON LOCALHOST.
    def makeDefaultLocalTestPermissionSets(self):
        noPermissionSetObjects = []
        for someTyping in self.manager.objectTyping:
            if(someTyping.permissionSets == []):
                noPermissionSetObjects.append(someTyping)
        for someTyping in noPermissionSetObjects:
            someTyping.permissionSets.append(
                polariPermissionSet(manager=self.manager, environment="localhost", setName="localHostTestPS_"+someTyping.className, apiObject=someTyping.className, forAllAnonymousUsers=True, assignedUserGroups=["AdminGroup"],
                functionsAll=True,createAll=True, readAll=True, updateAll=True, delete=True)
            )

    def setupExistingObjectAPIs(self):
        #Get all polytyped objects in the given manager objects
        #first get all of the Polari-Defined manager and tree objects
        #these will have certain restrictions placed on them that are necessary
        #in order to keep the entire system cohesive and not failing horribly.
        otherNonAPIenabledObjects = []
        treeObjectsList = []
        managersList = []
        accountedTypes = self.securityManagerObjects + self.protectedManagerObjects + self.publicManagersListmanagersList + self.securityTreeObjects + self.protectedTreeObjects + self.publicTreeObjectsList + self.apiRestrictedObjects
        #Get all objects that do not already have an indicated default typing.
        for someTyping in self.manager.polyTypedObjects:
            if(someTyping.isTreeObject == None or someTyping.isManagerObject):
                otherNonAPIenabledObjects.append(someTyping.className)
            elif(someTyping.isTreeObject and not someTyping.className in accountedTypes):
                treeObjectsList.append(someTyping.className)
            elif(someTyping.isManagerObject and not someTyping.className in accountedTypes):
                managersList.append(someTyping.className)
        for treeObjName in treeObjectsList:
            for someTyping in self.manager.polyTypedObjects:
                if(someTyping.className == treeObjName):
                    newPermissionSet = self.newDefaultPermissionSet(apiObject=treeObjName, isSecure=True)
                    newOwnerPermissionSet = self.newDefaultPermissionSet(apiObject=treeObjName, isOwnerPerms=True)
                    someTyping.permissionSets.append(newPermissionSet)
                    someTyping.permissionSets.append(newOwnerPermissionSet)
                    break

    def newDefaultPermissionSet(self, apiObject, isBasePS=False, isOwnerPerms=False, isSecure=False, isProtected=False, isPublic=False):
        if(isSecure):
            return polariPermissionSet(apiObject=apiObject, isGeneralized=isBasePS,
    functionsAll=False, functionsSpecific=[], createAll=False, createSpecific=[],
    readAll=False, readSpecific=[], updateAll=False, updateSpecific=[], delete=False,
    filter = [])
        elif(isProtected):
            return polariPermissionSet(apiObject=apiObject, isGeneralized=isBasePS,
    functionsAll=False, functionsSpecific=[], createAll=False, createSpecific=[],
    readAll=True, readSpecific=[], updateAll=False, updateSpecific=[], delete=False,
    filter = [])
        elif(isPublic):
            return polariPermissionSet(apiObject=apiObject, isGeneralized=isBasePS,
    functionsAll=False, functionsSpecific=[], createAll=True, createSpecific=[],
    readAll=True, readSpecific=[], updateAll=True, updateSpecific=[], delete=False,
    filter = [])
        elif(isOwnerPerms):
            return polariPermissionSet(apiObject=apiObject, isGeneralized=isBasePS,
    functionsAll=False, functionsSpecific=[], createAll=False, createSpecific=[],
    readAll=True, readSpecific=[], updateAll=True, updateSpecific=[], delete=True,
    filter = [apiObject + ' WHERE owner=var(someUser)'], userCriteriaSharingFilter=[])

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