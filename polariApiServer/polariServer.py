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
from polariApiServer.modulesAPI import ModulesAPI
from polariApiServer.displayDefinition import DisplayDefinition
from polariApiServer.tableDefinition import TableDefinition
from polariApiServer.graphDefinition import GraphDefinition
from polariApiServer.geoJsonDefinition import GeoJsonDefinition
from polariApiServer.tileSourceDefinition import TileSourceDefinition
from polariApiServer.geocoderDefinition import GeocoderDefinition
from polariApiServer.updateClassConfigAPI import UpdateClassConfigAPI
from polariApiServer.systemInfoAPI import systemInfoAPI
from polariApiServer.apiFormatConfig import ApiFormatConfig
from polariApiServer.configuredFormattedAPIs import FlatJsonAPI, D3ColumnAPI, GeoJsonAPI
from polariApiServer.tileGeneratorAPI import TileGeneratorAPI
from polariApiServer.objectStorageAPI import ObjectStorageAPI
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


class CORSExtraHeadersMiddleware:
    """Adds CORS headers that Falcon 4.x built-in CORSMiddleware doesn't cover.
    Falcon's CORSMiddleware handles Allow-Origin, Allow-Credentials, and OPTIONS preflight.
    This adds Allow-Headers and Max-Age which are needed for preflight responses.
    Note: In staging/prod, nginx also sets these headers. Duplicates are tolerated."""
    def process_response(self, req, resp, resource, req_succeeded):
        resp.set_header('Access-Control-Allow-Headers',
                        'Content-Type, Authorization, Accept, Origin, X-Requested-With')
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
        # Configure CORS: Falcon 4.x built-in handles Origin, Credentials, and OPTIONS preflight.
        # CORSExtraHeadersMiddleware adds Allow-Headers and Max-Age.
        # In staging/prod, nginx also handles CORS (including OPTIONS interception).
        allow_origins = '*' if '*' in CORS_ORIGINS else CORS_ORIGINS
        allow_creds = '*' if '*' in CORS_ORIGINS else allow_origins
        self.falconServer = falcon.App(
            middleware=[
                falcon.CORSMiddleware(allow_origins=allow_origins, allow_credentials=allow_creds),
                CORSExtraHeadersMiddleware()
            ]
        )
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

        # Create Module Management endpoint for enabling/disabling modules
        modulesEndpoint = ModulesAPI(polServer=self, manager=self.manager)

        # Create System Info endpoint for diagnostics and resource profiling
        systemInfoEndpoint = systemInfoAPI(polServer=self, manager=self.manager)

        # Create endpoint for updating class configuration flags
        updateClassConfigEndpoint = UpdateClassConfigAPI(polServer=self, manager=self.manager)

        # Create Tile Generator endpoint for .mbtiles generation
        tileGeneratorEndpoint = TileGeneratorAPI(polServer=self, manager=self.manager)

        # Create Object Storage endpoint for MinIO connection management
        objectStorageEndpoint = ObjectStorageAPI(polServer=self, manager=self.manager)

        # Register APIProfile, APIDomain, APIEndpoint, and ApiFormatConfig types
        self.manager.getObjectTyping(classObj=APIProfile)
        self.manager.getObjectTyping(classObj=APIDomain)
        self.manager.getObjectTyping(classObj=APIEndpoint)
        self.manager.getObjectTyping(classObj=ApiFormatConfig)
        # Register Definition classes and configure them for CRUDE access.
        # By default polyTypedObject sets excludeFromCRUDE=True; override for
        # these data-container classes so the frontend knows CRUDE is available.
        # Also pre-populate polyTypedVars from the class signature since there
        # are no instances at startup for runAnalysis() to inspect.
        self.defClassList = [DisplayDefinition, TableDefinition, GraphDefinition, GeoJsonDefinition, TileSourceDefinition, GeocoderDefinition]
        print(f'[DefInit] Registering {len(self.defClassList)} definition classes', flush=True)
        for defClass in self.defClassList:
            className = defClass.__name__
            defTyping = self.manager.getObjectTyping(classObj=defClass)
            if defTyping is not None:
                defTyping.excludeFromCRUDE = False
                defTyping.isDefinitionClass = True
                created = defTyping.initializeVarsFromSignature()
                print(f'[DefInit] {className}: polyTypedVarsDict keys={list(defTyping.polyTypedVarsDict.keys())}, identifiers={defTyping.identifiers}, created={created}', flush=True)
            else:
                print(f'[DefInit] {className}: getObjectTyping returned None!', flush=True)
        # NOTE: DB table creation and instance restoration happen later via
        # ensureDefinitionTables(), called from managerObject.__init__ AFTER
        # jumpstartDatabase() completes (self.manager.db is still None here).

        # NOTE: _autoRegisterMbtilesSources() is called from the manager's
        # __init__ after jumpstartObjectStore() completes, since object storage
        # is not yet connected at this point in polariServer.__init__.

        self.customAPIsList = [serverTouchPointAPI, tempRegisterAPI, managerObjectEndpoint, polyTypedObjectEndpoint, classInstanceCountsEndpoint, createClassEndpoint, stateSpaceClassesEndpoint, stateSpaceConfigEndpoint, stateDefinitionEndpoint, apiProfilerQueryEndpoint, apiProfilerMatchEndpoint, apiProfilerBuildEndpoint, apiProfilerCreateClassEndpoint, apiProfilerTemplatesEndpoint, apiProfilerDetectTypesEndpoint, apiDomainEndpoint, apiEndpointEndpoint, apiEndpointFetchEndpoint, apiConfigEndpoint, systemInfoEndpoint, updateClassConfigEndpoint, tileGeneratorEndpoint, objectStorageEndpoint]

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
        # Gate on configuration - default disabled
        self._materials_science_classes = []
        ms_enabled = False
        try:
            from config_loader import config as ms_config
            ms_enabled = ms_config.get('modules.materials_science.enabled', False)
            if isinstance(ms_enabled, str):
                ms_enabled = ms_enabled.lower() in ('true', '1', 'yes')
        except ImportError:
            pass

        if MATERIALS_SCIENCE_AVAILABLE and ms_enabled:
            try:
                print("[MS-Module-Load] [polariServer] Materials Science module enabled — beginning initialization")
                include_seed = True
                try:
                    from config_loader import config as seed_config
                    include_seed = seed_config.get('modules.materials_science.include_seed_data', True)
                except ImportError:
                    pass
                print(f"[MS-Module-Load] [polariServer] objectTypingDict BEFORE init: {len(self.manager.objectTypingDict)} entries")
                result = initialize_materials_science(
                    manager=self.manager,
                    include_seed_data=include_seed
                )
                print(f"[MS-Module-Load] [polariServer] objectTypingDict AFTER init: {len(self.manager.objectTypingDict)} entries")
                self._materials_science_classes = list(result['registered_classes'].keys())
                # Auto-register CRUDE endpoints for all module classes
                crude_ok = 0
                crude_fail = 0
                for class_name in result['registered_classes']:
                    try:
                        self.registerCRUDEforObjectType(class_name)
                        crude_ok += 1
                    except Exception as ce:
                        crude_fail += 1
                        print(f"[MS-Module-Load] [polariServer] CRUDE registration failed for {class_name}: {ce}")
                seed_count = sum(len(v) for v in result['seed_data'].values())
                print(f"[MS-Module-Load] [polariServer] Init complete: {len(result['registered_classes'])} classes, {crude_ok} CRUDE endpoints, {crude_fail} CRUDE failures, {seed_count} seed records")
            except Exception as e:
                print(f"[MS-Module-Load] [polariServer] ERROR: Could not initialize Materials Science module: {e}")
                import traceback
                traceback.print_exc()
        elif not ms_enabled:
            print("[MS-Module-Load] [polariServer] Materials Science module disabled by configuration")

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

    def ensureDefinitionTables(self):
        """Create DB tables for Definition classes and restore saved instances.

        Called from managerObject.__init__ AFTER jumpstartDatabase() completes,
        because self.manager.db is None when polariServer.__init__ runs.
        This method:
        1. Creates missing tables for each Definition class
        2. Migrates old tables that lack an 'id' column
        3. Restores previously-saved Definition instances from the DB
        """
        db = self.manager.db
        if db is None:
            print('[DefInit] ensureDefinitionTables: no database, skipping', flush=True)
            return
        print(f'[DefInit] ensureDefinitionTables: db.tables={db.tables}', flush=True)
        for defClass in self.defClassList:
            className = defClass.__name__
            defTyping = self.manager.objectTypingDict.get(className)
            if defTyping is None:
                print(f'[DefInit] {className}: not in objectTypingDict, skipping', flush=True)
                continue
            if className not in db.tables:
                if defTyping.polyTypedVarsDict:
                    print(f'[DefInit] {className}: creating DB table', flush=True)
                    try:
                        defTyping.makeTypedTableFromAnalysis()
                    except Exception as e:
                        print(f'[DefInit] DB table creation failed for {className}: {e}', flush=True)
                        import traceback
                        traceback.print_exc()
                else:
                    print(f'[DefInit] {className}: no polyTypedVarsDict, cannot create table', flush=True)
            else:
                # Table exists — verify it has an 'id' column
                self._migrateDefinitionTable(className)
        print(f'[DefInit] DB tables after ensureDefinitionTables: {db.tables}', flush=True)
        # Now restore any saved Definition instances
        self._restoreDefinitionInstances(self.defClassList)

    def _migrateDefinitionTable(self, className):
        """Check if a Definition table has an 'id' column and recreate it if not.

        Older versions created tables without an 'id' PRIMARY KEY because
        initializeVarsFromSignature() skipped the 'id' parameter. This
        method detects the old schema and recreates the table with the
        correct structure so instances can be properly persisted.
        """
        import sqlite3
        db = self.manager.db
        if db is None:
            return
        try:
            dbFilePath = os.path.join(db.Path, db.name + '.db') if db.Path else db.name + '.db'
            conn = sqlite3.connect(dbFilePath)
            cursor = conn.execute(f"PRAGMA table_info({className})")
            columns = [row[1] for row in cursor.fetchall()]
            conn.close()
            if 'id' not in columns:
                print(f'[polariServer] Migrating {className} table: adding "id" column (recreating table)', flush=True)
                # Drop the old table (it has no usable data without IDs)
                conn = sqlite3.connect(dbFilePath)
                conn.execute(f'DROP TABLE IF EXISTS {className}')
                conn.commit()
                conn.close()
                # Remove from tables list so makeTypedTableFromAnalysis can recreate
                if className in db.tables:
                    db.tables.remove(className)
                # Recreate with correct schema
                typingObj = self.manager.objectTypingDict.get(className)
                if typingObj:
                    typingObj.makeTypedTableFromAnalysis()
        except Exception as e:
            print(f'[polariServer] Migration check failed for {className}: {e}', flush=True)

    def _restoreDefinitionInstances(self, defClassList):
        """Restore Definition instances (Table/Graph/Display/GeoJson) from DB.

        These classes are registered in objectTypingDict after
        jumpstartDatabase() → restoreFromDatabase() has already run,
        so their table rows were skipped during the main restore pass.
        This method performs a targeted restore for those classes only.
        """
        db = self.manager.db
        if db is None:
            print('[DefRestore] No database, skipping restore', flush=True)
            return
        import json as jsonLib
        for defClass in defClassList:
            className = defClass.__name__
            if className not in db.tables:
                print(f'[DefRestore] {className}: not in db.tables, skipping', flush=True)
                continue
            # Skip if instances already exist (e.g. from another restore path)
            existing = self.manager.objectTables.get(className, {})
            if existing:
                print(f'[DefRestore] {className}: {len(existing)} instances already in objectTables, skipping', flush=True)
                continue
            try:
                columnNames, dataTuples = db.getAllInTable(className)
            except Exception as e:
                print(f'[DefRestore] {className}: Error reading table: {e}', flush=True)
                continue
            print(f'[DefRestore] {className}: columns={columnNames}, rows={len(dataTuples)}', flush=True)
            if not dataTuples:
                print(f'[DefRestore] {className}: no rows in DB', flush=True)
                continue
            restoredCount = 0
            for row in dataTuples:
                # Build kwargs from DB columns matching constructor params
                initKwargs = {'manager': self.manager}
                for i, colName in enumerate(columnNames):
                    if colName == '_branch_path':
                        continue
                    if row[i] is not None:
                        initKwargs[colName] = row[i]
                print(f'[DefRestore] {className}: restoring with kwargs keys={list(initKwargs.keys())}', flush=True)
                try:
                    instance = defClass(**initKwargs)
                    restoredCount += 1
                    print(f'[DefRestore] {className}: restored instance id={getattr(instance, "id", "?")}', flush=True)
                except Exception as e:
                    print(f'[DefRestore] {className}: Error restoring instance: {e}', flush=True)
                    import traceback
                    traceback.print_exc()
            if restoredCount > 0:
                print(f'[DefRestore] Restored {restoredCount} {className} instances from DB', flush=True)

    def _autoRegisterMbtilesSources(self):
        """Scan MinIO buckets for .mbtiles files and create or update
        TileSourceDefinition instances so tile-serving works correctly.

        This ensures that previously generated tile sources survive server
        restarts and that old-format definitions get migrated to the new
        tileserver-based format with proper bucket/objectName fields.
        """
        store = getattr(self.manager, 'objectStore', None)
        if store is None or not store.connected:
            print('[polariServer] Auto-register: objectStore not connected, skipping', flush=True)
            return

        import json as jsonLib

        # Build lookup of existing TileSourceDefinition instances by name
        existing_by_name = {}
        ts_table = self.manager.objectTables.get('TileSourceDefinition', {})
        if isinstance(ts_table, dict):
            for defId, inst in ts_table.items():
                existing_by_name[getattr(inst, 'name', '')] = (defId, inst)
        elif isinstance(ts_table, list):
            for inst in ts_table:
                existing_by_name[getattr(inst, 'name', '')] = (getattr(inst, 'polariId', ''), inst)

        print(f'[polariServer] Auto-register: found {len(existing_by_name)} existing TileSourceDefinition(s): {list(existing_by_name.keys())}', flush=True)

        registered = 0
        updated = 0
        try:
            buckets = store.list_buckets()
            print(f'[polariServer] Auto-register: MinIO buckets: {buckets}', flush=True)
        except Exception as e:
            print(f'[polariServer] Auto-register: failed to list buckets: {e}', flush=True)
            return

        for bucket in buckets:
            try:
                objects = store.list_objects(bucket)
            except Exception:
                continue
            for obj in objects:
                obj_name = obj.get('name', '')
                if not obj_name.endswith('.mbtiles'):
                    continue
                # Derive a readable name from the filename (strip extension)
                source_name = obj_name.rsplit('.', 1)[0]

                # Build the correct definition JSON
                new_definition = jsonLib.dumps({
                    'type': 'vector',
                    'url': f'/tiles/{source_name}/{{z}}/{{x}}/{{y}}.pbf',
                    'bucket': bucket,
                    'objectName': obj_name,
                    'attribution': 'Generated by Polari Tile Generator',
                    'tileFormat': 'vector',
                    'sourceLayer': 'default',
                    'defaultCenter': None,
                    'defaultZoom': None
                })

                if source_name in existing_by_name:
                    # Check if the existing definition needs updating
                    defId, inst = existing_by_name[source_name]
                    old_def_str = getattr(inst, 'definition', '{}')
                    old_type = getattr(inst, 'type', '')
                    try:
                        old_def = jsonLib.loads(old_def_str) if isinstance(old_def_str, str) else old_def_str
                    except (jsonLib.JSONDecodeError, ValueError):
                        old_def = {}

                    needs_update = (
                        old_type != 'tileserver' or
                        'bucket' not in old_def or
                        'objectName' not in old_def or
                        old_def.get('type') != 'vector'
                    )
                    print(f'[polariServer] Auto-register: "{source_name}" exists (type={old_type}), needs_update={needs_update}', flush=True)
                    if needs_update:
                        print(f'[polariServer] Auto-register: updating "{source_name}" old_def={old_def_str}', flush=True)
                        inst.type = 'tileserver'
                        inst.definition = new_definition
                        if self.manager.db is not None:
                            try:
                                self.manager.db.saveInstanceInDB(inst)
                            except Exception as db_err:
                                print(f'[polariServer] Auto-register: DB update failed for {source_name}: {db_err}', flush=True)
                        updated += 1
                    continue

                # Create new TileSourceDefinition
                try:
                    instance = TileSourceDefinition(
                        name=source_name, type='tileserver',
                        definition=new_definition, manager=self.manager
                    )
                    # Persist to DB if available
                    if self.manager.db is not None:
                        try:
                            self.manager.db.saveInstanceInDB(instance)
                        except Exception as db_err:
                            print(f'[polariServer] Auto-register: DB save failed for {source_name}: {db_err}', flush=True)
                    existing_by_name[source_name] = (getattr(instance, 'polariId', ''), instance)
                    registered += 1
                    print(f'[polariServer] Auto-register: created new "{source_name}" in bucket "{bucket}"', flush=True)
                except Exception as e:
                    print(f'[polariServer] Auto-register: failed to create TileSourceDefinition for {source_name}: {e}', flush=True)

        print(f'[polariServer] Auto-register complete: {registered} new, {updated} updated', flush=True)

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

