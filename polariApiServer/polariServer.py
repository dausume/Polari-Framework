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
from polariNetworking.defineLocalSys import *
from objectTreeDecorators import *
from polariApiServer.dataStreams import *
from polariFiles.dataChannels import *
from polariFiles.managedFiles import *
from polariApiServer.polariCRUDE import polariCRUDE
from polariApiServer.polariAPI import polariAPI
from polariApiServer.managerObjectAPI import managerObjectAPI
from polariApiServer.polyTypedObjectAPI import polyTypedObjectAPI
from polariApiServer.classInstanceCountsAPI import classInstanceCountsAPI
from polariApiServer.apiDiscoveryAPI import APIDiscoveryAPI
from polariApiServer.createClassAPI import createClassAPI
from polariApiServer.stateSpaceAPI import StateSpaceClassesAPI, StateSpaceConfigAPI, StateDefinitionAPI
from polariApiServer.apiConfigAPI import ApiConfigAPI
from polariApiServer.apiFormatConfig import ApiFormatConfig
from polariApiServer.flatJsonAPI import FlatJsonAPI
from polariApiServer.d3ColumnAPI import D3ColumnAPI
from polariApiProfiler.apiProfilerAPI import (
    APIProfilerQueryAPI,
    APIProfilerMatchAPI,
    APIProfilerBuildAPI,
    APIProfilerCreateClassAPI,
    APIProfilerTemplatesAPI,
    APIProfilerDetectTypesAPI,
    APIDomainAPI,
    APIEndpointAPI,
    APIEndpointFetchAPI
)
from polariApiProfiler.apiProfile import APIProfile
from polariApiProfiler.apiDomain import APIDomain
from polariApiProfiler.apiEndpoint import APIEndpoint
from accessControl.polariPermissionSet import polariPermissionSet
from accessControl.polariUserGroup import UserGroup
from accessControl.polariUser import User
from wsgiref import simple_server
import falcon
import secrets
import subprocess

# Import Materials Science module
try:
    from polariMaterialsScienceModule import initialize as initialize_materials_science
    MATERIALS_SCIENCE_AVAILABLE = True
except ImportError:
    MATERIALS_SCIENCE_AVAILABLE = False
    print("[polariServer] Materials Science module not available - skipping")

# Import configuration loader for CORS origins
try:
    from config_loader import config
    CORS_ORIGINS = config.get('api.cors_origins', ['*'])
    # If it's a string (from env var), split it
    if isinstance(CORS_ORIGINS, str):
        CORS_ORIGINS = [o.strip() for o in CORS_ORIGINS.split(',')]
except ImportError:
    # Fallback if config_loader not available
    CORS_ORIGINS = ['*']


class CORSMiddleware:
    """
    Custom CORS middleware for Falcon.
    Handles preflight OPTIONS requests and adds CORS headers to responses.
    """
    def __init__(self, allow_origins=None, allow_methods=None, allow_headers=None, allow_credentials=True):
        self.allow_origins = allow_origins or ['*']
        self.allow_methods = allow_methods or ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS']
        self.allow_headers = allow_headers or ['Content-Type', 'Authorization', 'Accept', 'Origin', 'X-Requested-With']
        self.allow_credentials = allow_credentials

    def process_request(self, req, resp):
        # Handle preflight OPTIONS requests
        if req.method == 'OPTIONS':
            resp.complete = True

    def process_response(self, req, resp, resource, req_succeeded):
        origin = req.get_header('Origin')

        # Check if origin is allowed
        if origin:
            if '*' in self.allow_origins or origin in self.allow_origins:
                resp.set_header('Access-Control-Allow-Origin', origin)
            elif self.allow_origins == ['*']:
                resp.set_header('Access-Control-Allow-Origin', '*')

        resp.set_header('Access-Control-Allow-Methods', ', '.join(self.allow_methods))
        resp.set_header('Access-Control-Allow-Headers', ', '.join(self.allow_headers))

        if self.allow_credentials:
            resp.set_header('Access-Control-Allow-Credentials', 'true')

        # Handle max age for preflight caching
        resp.set_header('Access-Control-Max-Age', '86400')

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
        #Creates a random salt for hashing passwords for validating users.
        #THE VALUES IN THIS DICT SHOULD NOT BE CHANGED OR ALL PASSWORDS WILL BE RESET.
        #Contains a set of salts that define password hashes for given time periods
        #or just a * for all time periods.
        self.serverPasswordSaltDict = {"*":secrets.token_urlsafe(16)}
        #Temporary Users and Registered Users should be at least equal so that all Users can
        #login simultaneously if needed, so long as no unaccounted for or malicious people or bots
        #are attempting to occupy space as temporary Users.
        #Analysis of the server overall should be made to determine what these limits
        #should be set as.
        self.temporaryUsersLimit = 10
        self.registeredUsersLimit = 10
        self.displayName = displayName
        #Password requirements
        self.passwordRequirements = {"min-length":8, "max-length":24, "min-special-chars":1, "min-nums":2}
        self.publicFrontendKey = None
        self.privateFrontendKey = None
        # Configure CORS with allowed origins from config
        cors_middleware = CORSMiddleware(allow_origins=CORS_ORIGINS, allow_credentials=True)
        self.falconServer = falcon.App(middleware=[cors_middleware])
        self.active = False
        #Defines endpoints or mapping to remote endpoints which allow for CRUD access to all objects of the server's manager as well as it's subordinate manager objects.
        managerIdTuple = self.manager.getInstanceIdentifiers(self.manager)
        self.objectEndpoints = {}
        #Defines endpoints or mapping to remote endpoints which allow for CRUD access through dataChannel specifications on a server's manager as well as it's subordinate manager objects.
        self.dataChannelEndpoints = {}
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
        #print('Typing Dict for polServer: ')
        #Get the typing for the manager object which houses this server.
        managerType = type(self.manager).__name__
        #SECURE: Does not grant any visibility by default.
        self.secureManagerObjects = []
        #PROTECTED: Grants only read by default.
        self.protectedManagerObjects = [managerType]
        self.tempUsersList = []
        self.tempUsersDict = {}
        self.usersList = [User(username="topadmin", password="topadmin", manager=self.manager)]
        self.usersDict = {self.usersList[0].username:self.usersList[0]}
        self.userGroupsList = [UserGroup(name="adminGroup", assignedUsers=[self.usersList[0]], manager=self.manager)]
        self.userGroupsDict = {self.userGroupsList[0].name:self.userGroupsList[0]}
        #PUBLIC: Anyone with access to read all and create by default.
        #anything which someone has created will be granted modify access by default.
        #Secondary permissions grant update based on creators or other criteria.
        self.managersOnServer = [self.manager]
        self.publicManagersList = []
        self.apiRestrictedObjects = ["isoSys"]
        self.secureTreeObjects = []
        self.protectedTreeObjects = ["polyTypedObject", "polyTypedVar", "polariServer", "managedDatabase"]
        self.publicTreeObjectsList = []
        #Creates an endpoint for the given manager object for the specific channel object Ex:
        #  https://someURL.com/manager-managerObjectType-(id0:val0, id1:val1, id2:val2, ...)/channel/channelName
        self.uriList = []
        objList = [self, self.manager]
        serverTouchPointAPI = polariAPI(apiName='', polServer=self, minAccessDict={'R':{"polariAPI":"*","polariCRUDE":"*", "polariServer":"*", "polyTypedObject":"*", "polyTypedVariable":"*"}}, minPermissionsDict={'R':{"polariAPI":"*","polariCRUD":"*", "polariServer":"*"}}, manager=self.manager)
        #Create User API - Creates an API for the user to temporarily register with until they either login or create their own actual registration.
        tempRegisterAPI = polariAPI(apiName='tempRegister', polServer=self, minAccessDict={'E':{"polariServer":"*"}}, minPermissionsDict={'E':{"polariServer":"tempRegister"}}, manager=self.manager)
        #Update temp registration to actual registration
        registerAPI = polariAPI(apiName='register', polServer=self, minAccessDict={'E':{"polariServer":"*"}}, minPermissionsDict={'E':{"polariServer":"register"}}, manager=self.manager)
        #Change over to the official registration, transfer over all instances owned by the current temporary registration
        #to the official one.  Then delete the temporary registration.
        loginAPI = polariAPI(apiName='login', polServer=self, minAccessDict={'E':{"polariServer":"*"}}, minPermissionsDict={'E':{"polariServer":"login"}}, manager=self.manager)

        # Create custom endpoint for managerObject
        managerObjectEndpoint = managerObjectAPI(polServer=self, manager=self.manager)

        # Create custom endpoint for polyTypedObject
        polyTypedObjectEndpoint = polyTypedObjectAPI(polServer=self, manager=self.manager)

        # Create custom endpoint for class instance counts (used/unused classes)
        classInstanceCountsEndpoint = classInstanceCountsAPI(polServer=self, manager=self.manager)

        # Create API discovery endpoint (lists all available endpoints)
        apiDiscoveryEndpoint = APIDiscoveryAPI(polServer=self, manager=self.manager)

        # Create custom endpoint for dynamic class creation
        createClassEndpoint = createClassAPI(polServer=self, manager=self.manager)

        # Create state-space API endpoints for no-code system
        stateSpaceClassesEndpoint = StateSpaceClassesAPI(polServer=self, manager=self.manager)
        stateSpaceConfigEndpoint = StateSpaceConfigAPI(polServer=self, manager=self.manager)
        stateDefinitionEndpoint = StateDefinitionAPI(polServer=self, manager=self.manager)

        # Create API Profiler endpoints
        apiProfilerQueryEndpoint = APIProfilerQueryAPI(polServer=self, manager=self.manager)
        apiProfilerMatchEndpoint = APIProfilerMatchAPI(polServer=self, manager=self.manager)
        apiProfilerBuildEndpoint = APIProfilerBuildAPI(polServer=self, manager=self.manager)
        apiProfilerCreateClassEndpoint = APIProfilerCreateClassAPI(polServer=self, manager=self.manager)
        apiProfilerTemplatesEndpoint = APIProfilerTemplatesAPI(polServer=self, manager=self.manager)
        apiProfilerDetectTypesEndpoint = APIProfilerDetectTypesAPI(polServer=self, manager=self.manager)

        # Create API Domain and Endpoint management endpoints
        apiDomainEndpoint = APIDomainAPI(polServer=self, manager=self.manager)
        apiEndpointEndpoint = APIEndpointAPI(polServer=self, manager=self.manager)
        apiEndpointFetchEndpoint = APIEndpointFetchAPI(polServer=self, manager=self.manager)

        # Create API Configuration endpoint for viewing/managing CRUDE permissions
        apiConfigEndpoint = ApiConfigAPI(polServer=self, manager=self.manager)

        # Register APIProfile, APIDomain, APIEndpoint, and ApiFormatConfig types
        self.manager.getObjectTyping(classObj=APIProfile)
        self.manager.getObjectTyping(classObj=APIDomain)
        self.manager.getObjectTyping(classObj=APIEndpoint)
        self.manager.getObjectTyping(classObj=ApiFormatConfig)

        self.customAPIsList = [serverTouchPointAPI, tempRegisterAPI, managerObjectEndpoint, polyTypedObjectEndpoint, classInstanceCountsEndpoint, createClassEndpoint, stateSpaceClassesEndpoint, stateSpaceConfigEndpoint, stateDefinitionEndpoint, apiProfilerQueryEndpoint, apiProfilerMatchEndpoint, apiProfilerBuildEndpoint, apiProfilerCreateClassEndpoint, apiProfilerTemplatesEndpoint, apiProfilerDetectTypesEndpoint, apiDomainEndpoint, apiEndpointEndpoint, apiEndpointFetchEndpoint, apiConfigEndpoint]

        # Populate uriList with custom API endpoints for overlap tracking
        for api in self.customAPIsList:
            apiName = getattr(api, 'apiName', '')
            if apiName and apiName not in self.uriList:
                self.uriList.append(apiName)

        self.crudeObjectsList = [polariCRUDE(apiObject="polariCRUDE", polServer=self, manager=self.manager)]
        objNamesList = list(self.manager.objectTypingDict)
        if(not "polariAPI" in objNamesList):
            objNamesList.append("polariAPI")
        if(not "polariCRUDE" in objNamesList):
            objNamesList.append("polariCRUDE")

        # Filter out core system objects that shouldn't have CRUDE endpoints
        # Note: polyTypedObject needs BOTH CRUDE (for frontend services) AND custom API (for typing-info page)
        excludedFromCRUDE = ["managerObject"]
        objNamesList = [obj for obj in objNamesList if obj not in excludedFromCRUDE]

        print("="*70)
        print("CRUDE ENDPOINTS BEING CREATED:")
        print(objNamesList)
        print("="*70)
        for objType in objNamesList:
            typingObj = self.manager.objectTypingDict[objType]
            typingObj.runAnalysis()
            newCRUDE = polariCRUDE(apiObject=objType, polServer=self, manager=self.manager)
            self.crudeObjectsList.append(newCRUDE)
            if newCRUDE.apiName not in self.uriList:
                self.uriList.append(newCRUDE.apiName)
            # Set the polariTree endpoint on the ApiFormatConfig if it exists
            if hasattr(typingObj, 'apiFormatConfig') and typingObj.apiFormatConfig is not None:
                typingObj.apiFormatConfig.polariTreeEndpoint = newCRUDE.apiName
            print(f"✓ Created CRUDE endpoint: {newCRUDE.apiName} for {objType}")
        
        
        #mainChannelURI = self.baseURIprefix + 'channel/' + self.serverChannel.name + '/' + self.baseURIpostfix
        #print('Template URI: ', templateURI)
        #self.crudObjectsList.append(polariCRUD(self.serverChannel, manager=self.manager))
        #self.apiServer.add_route(uri_template = mainChannelURI, resource= self.crudObjectsList[0] )
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

        # Initialize Materials Science module: register classes + auto-expose CRUDE endpoints
        if MATERIALS_SCIENCE_AVAILABLE:
            try:
                result = initialize_materials_science(
                    manager=self.manager,
                    include_seed_data=True
                )
                # Auto-register CRUDE endpoints for all module classes
                for class_name in result['registered_classes']:
                    try:
                        self.registerCRUDEforObjectType(class_name)
                    except Exception:
                        pass  # Skip classes that can't be CRUDE-registered (framework internals)
                seed_count = sum(len(v) for v in result['seed_data'].values())
                print(f"[polariServer] Materials Science initialized: {len(result['registered_classes'])} classes, {seed_count} seed records")
            except Exception as e:
                print(f"[polariServer] Warning: Could not initialize Materials Science module: {e}")

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

    def tempRegister(self):
        #First, check if the maximum allowed amount of tempUsers has been reached.
        #If limit has been reached, return an error saying limit was reached.
        if(len(self.tempUsersList) > self.temporaryUsersLimit):
            raise PermissionError("Maximum amount of temporarry users reached for this server.")
        else:
            #Else, create the new temporary user and return it's info to the frontend. 
            newTempUser = User(unregistered=True)
            self.tempUsersList.append(newTempUser)
            self.tempUsersDict[newTempUser.id] = newTempUser
            return newTempUser

    def register(self, tempUserId, newUsername, newPassword):
        cur_user = self.tempUsersDict[tempUserId]
        usernames = list(self.usersDict.keys())
        if(newUsername in usernames):
            raise ValueError("Username already has associated user.")
        

    def login(self, tempUserId, username, password):
        getTempUser = ""
        transferTempUserData = ""

    def changePassword(self, newPassword):
        if(len(newPassword) < self.passwordRequirements["min-length"]):
            raise ValueError("Must have over ", self.passwordRequirements["min-length"], " characters in password.")
        if(len(newPassword) < self.passwordRequirements["max-length"]):
            raise ValueError("Must have under ", self.passwordRequirements["max-length"], " characters in password.")
        specialCharCount = 0
        numCharCount = 0
        for someChar in newPassword:
            if(not someChar.isalnum()):
                specialCharCount += 1
            if(someChar.isnumeric()):
                numCharCount += 1
        if(specialCharCount < self.passwordRequirements["min-special-chars"]):
            raise ValueError("Must have over ", self.passwordRequirements["min-special-chars"], " special characters in password.")
        if(numCharCount < self.passwordRequirements["min-nums"]):
            raise ValueError("Must have over ", self.passwordRequirements["min-nums"], " numbers in password.")

    def registerCRUDEforObjectType(self, objType):
        """
        Dynamically register a CRUDE endpoint for an object type.
        This is useful when object types are registered after server initialization.

        Args:
            objType: The class name (string) of the object type to register

        Returns:
            The polariCRUDE instance that was created, or None if excludeFromCRUDE is True
        """
        if objType not in self.manager.objectTypingDict:
            raise ValueError(f"Object type '{objType}' not found in manager.objectTypingDict. Register the object type first using manager.getObjectTyping().")

        # Get typing object to check configuration flags
        typingObj = self.manager.objectTypingDict[objType]

        # Check if this object type should be excluded from CRUDE API
        # Core framework objects may set this to True to prevent runtime issues
        if hasattr(typingObj, 'excludeFromCRUDE') and typingObj.excludeFromCRUDE:
            print(f"Object type '{objType}' has excludeFromCRUDE=True, skipping CRUDE endpoint registration")
            return None

        # Check if CRUDE endpoint already exists for this type
        for crude in self.crudeObjectsList:
            if crude.apiObject == objType:
                print(f"CRUDE endpoint for '{objType}' already exists at {crude.apiName}")
                return crude

        # Run analysis on the typing object
        typingObj.runAnalysis()

        # Create new CRUDE endpoint
        newCRUDE = polariCRUDE(apiObject=objType, polServer=self, manager=self.manager)
        self.crudeObjectsList.append(newCRUDE)

        print(f"Registered CRUDE endpoint for '{objType}' at {newCRUDE.apiName}")
        return newCRUDE

