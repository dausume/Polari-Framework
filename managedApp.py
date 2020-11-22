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
from managedUserInterface import *
from dataChannels import *
from dataStreams import *
from managedDB import *
from managedExecutables import *
from managedFiles import *
from managedFolders import *
from managedImages import *
from remoteEvents import *
from polyTyping import *
from objectTreeManagerDecorators import *
import os, webbrowser, urllib.request, urllib.parse, datetime, time

class managedApp(managedFolder):
    #Defines what type of Framework functionality is pulled on to create the App
    #Defines what allowed types of apps can be instantiated.
    allowedAppTypes = ['PolariElectronApp']
    #Defines what type of files are used to hold data and how that data is distributed
    #and shared with other servers or systems.
    #Localized: All data is held in JSON files and managed by the polari itself.
    #StandAloneServer_closed: All data is held in a single Database File, but does not allow access anywhere.
    #StandAloneServer_open: All data is held in a single Database File, and allows access through https
    #requests for certain endpoints.
    distributionTypes = ['Localized']
    #Additional Statuses which may be applied onto the 'Statuses' variable, which are important only to Applications.
    statusSet = ['launchable','Channels-Complete','Channels-Incomplete','Pages-Incomplete','Pages-Complete']

    @managerObject
    def __init__(self, name=None, displayName=None, Path=None, manager=None):
        managedFolder.__init__(self, name=name, Path=Path, manager=manager)
        #Says whether or not the Application is meant to be running synchronously
        #with it's manager object's event loop, or on it's own event loop.
        self.managerSync = True
        self.appType = 'PolariWebApp'
        self.displayName = displayName
        self.distributionType = 'HTTPS'
        #Determines whether the Application Loop should be running.
        self.activeApp = False
        #The time (in minutes) after which, if the app has recieved no more requests, it will
        #time-out, effectively changing self.activeApp = False and closing out the App.
        self.lastRequestTime = None
        self.timeout = 3
        #The Server Data Channel which may collect requests and data in regards to any given page in the Application
        self.serverChannel = None
        #A data Channel exclusively used by Local Application User Interfaces.
        self.localAppChannel = None
        #Specifies which of the browserSourcePages is the first to be launched in order to begin execution of the App.
        self.landingSourcePage = None
        #The Database for the Application which holds all data for it.
        self.DB = None
        #A list of all directories within this app's Directory Tree that are sub-apps contained within it.
        self.subApps = []
        #The Source Pages of the Application, each of which provides data to client side when an instance of it's page
        #is created and also collects requests and data from their own instantiated pages in the Application.
        self.sourcePages = []
        #Contains the names of all files which exist in the main directory and any sub-directories (excluding sub-apps).
        #IN ADDITION TO any files that exist outside of the directory but are utilized for functions
        self.AppFiles = []
        #A list of User Interfaces (Defined as the Per-User,Per-System,Per-Browser Interfacing with this Application)
        #There may be multiple users on one system. EX: (Joe, sys1, Chrome), (Bob, sys1, Chrome), (Kara, sys1, Chrome)
        #There may also be a single user accessing from many locations. EX: (Joe, sys1, Chrome), (Joe, sys2, Chrome), (Joe, sys3, Chrome)
        #A single User may also access the Application from multiple Browsers. EX: (Joe, sys1, Chrome), (Joe, sys1, Microsoft Edge), (Joe, sys1, Chromium)
        self.UIs = []
        #Active Events are events that still need operations performed on them
        #by the App.  Awaiting Response Events are events that have been sent from
        #the App as a Source and have yet to recieve a response in regards to
        #the result or resolution of that event, or if it was successful.
        self.eventsToProcess = []
        self.eventsToSend = []
        self.eventsAwaitingResponse = []
        #Data Streams are used to regularly update dataChannels or regularly pull in data from them
        #in order to update the data in the system.
        #Requested: Data Streams requested through a channel are placed here until they are
        #set up properly and ready to be processed.
        self.dataStreamsRequested = []
        #Processed: Causes data to either be pulled from this server into the channel or from the
        #channel and into the server.
        self.dataStreamsToProcess = []
        #Awaiting Response: A non-recurring datastream has sent out it's data and is awaiting the
        #response 
        self.dataStreamsAwaitingResponse = []
        #Holds the data typing information and also links the particular objects that should be
        #considered as a part of or sub-part of this app.
        self.objectTyping = []

    def __setattr__(self, name, value):
        polyObj = self.objectTyping[type(self).__name__]
        #In polyObj 'polyObj.className' potential references exist for this object.
        #Here, we get each variable that is a reference or a list of references to a
        #particular type of object.
        if name in polyObj.objectReferencesDict:
            if(value == None or value == []):
                print(name + ' was assigned to be an empty variable')
            elif(type(value) == list):
                #Adding a list of objects
                for inst in value:
                    ids = self.getInstanceIdentifiers(inst)
                    instPath = self.getTuplePathInObjTree(instanceTuple=tuple([polyObj.className, ids, inst]))
                    if instPath == []:
                        continue
                    elif instPath == None:
                        newBranch = tuple([polyObj.className, ids, inst])
                        self.addNewBranch(traversalList=[], branchTuple=newBranch)
                    else:
                        #add as a duplicate branch
                        duplicateBranchTuple = tuple([polyObj.className, ids, tuple(valuePath)])
                        self.replaceOriginalTuple(self, originalPath=valuePath, newPath=[duplicateBranchTuple], newTuple=duplicateBranchTuple)
            else:
                #Adding one object
                ids = self.getInstanceIdentifiers(value)
                valuePath = self.getTuplePathInObjTree(instanceTuple=tuple([polyObj.className, ids, value]))
                if(valuePath == []):
                    #Do nothing, because the branch is already accounted for.
                    pass
                elif(valuePath == None):
                    #add the new Branch
                    newBranch = tuple([polyObj.className, ids, value])
                    self.addNewBranch(traversalList=[], branchTuple=newBranch)
                else:
                    #add as a duplicate branch
                    duplicateBranchTuple = tuple([polyObj.className, ids, tuple(valuePath)])
                    self.replaceOriginalTuple(self, originalPath=valuePath, newPath=[duplicateBranchTuple], newTuple=duplicateBranchTuple)
        #Throw event indicating that the variable was changed
        #WRITE CODE HERE
        #Assign the variable
        super(Attr, self).__setattr__(name, value)

    #Generates a new application with default file names databases and channels.
    def mkApp(self):
        self.mkDir()
        self.makeFile(name='serverChannel', extension='json')
        self.makeFile(name='localAppChannel', extension='json')
        self.makeFile(name=self.name, extension='db')
        self.DB = self.getActiveFile(name=self.name, extension= 'db')
        self.serverChannel = self.getActiveFile(name='serverChannel', extension='json')
        self.localAppChannel = self.getActiveFile(name='localAppChannel', extension='json')
        self.primePolyTyping()
        self.makeObjectTree()

    #Adds all of the basic objects that are necessary for the application to run, and accounts for
    #all of their identifiers.
    def primePolyTyping(self):
        source_Polari = self.makeFile(name='definePolari', extension='py')
        source_dataStream = self.makeFile(name='dataStreams', extension='py')
        source_remoteEvent = self.makeFile(name='remoteEvents', extension='py')
        source_managedUserInterface = self.makeFile(name='managedUserInterface', extension='py')
        source_managedFile = self.makeFile(name='managedFile', extension='py')
        #managedApp and browserSourcePage share the same source file.
        source_managedAppANDbrowserSourcePage = self.makeFile(name='managedApp', extension='py')
        source_managedDatabase = self.makeFile(name='managedDB', extension='py')
        source_dataChannel = self.makeFile(name='dataChannels', extension='py')
        source_managedExecutable = self.makeFile(name='managedExecutable', extension='py')
        #polyTyped Object and variable are both defined in the same source file
        source_polyTypedObjectANDvariables = self.makeFile(name='polyTypedObject', extension='py')
        self.objectTyping = [
            polyTypedObject(sourceFiles=[source_Polari], className='Polari', identifierVariables = ['identifier'], objectReferencesDict={'managedApp':['manager'],'polyTypedObject':['manager']}, manager=self),
            polyTypedObject(sourceFiles=[source_dataStream], className='dataStream', identifierVariables = ['identifier'], objectReferencesDict={'managedApp':['dataStreamsToProcess','dataStreamsRequested','dataStreamsAwaitingResponse']}, manager=self),
            polyTypedObject(sourceFiles=[source_remoteEvent], className='remoteEvent', identifierVariables = ['identifier'], objectReferencesDict={'managedApp':['eventsToProcess','eventsToSend','eventsAwaitingResponse']}, manager=self),
            polyTypedObject(sourceFiles=[source_managedUserInterface], className='managedUserInterface', identifierVariables = ['identifier'], objectReferencesDict={'managedApp':['UIs']}, manager=self),
            polyTypedObject(sourceFiles=[source_managedFile], className='managedFile', identifierVariables = ['name','extension','Path'], objectReferencesDict={'managedApp':['AppFiles']}, manager=self),
            polyTypedObject(sourceFiles=[source_managedAppANDbrowserSourcePage], className='managedApp', identifierVariables = ['name'], objectReferencesDict={'managedApp':['subApps','manager'],'polyTypedObject':['manager']}, manager=self),
            polyTypedObject(sourceFiles=[source_managedAppANDbrowserSourcePage], className='browserSourcePage', identifierVariables = ['name','Path'], objectReferencesDict={'managedApp':['landingSourcePage','sourcePages']}, manager=self),
            polyTypedObject(sourceFiles=[source_managedDatabase], className='managedDatabase', identifierVariables = ['name','Path'], objectReferencesDict={'managedApp':['DB']}, manager=self),
            polyTypedObject(sourceFiles=[source_dataChannel], className='dataChannel', identifierVariables = ['name','Path'], objectReferencesDict={'managedApp':['serverChannel','localAppChannel'],'managedSourcePage':['']}, manager=self),
            polyTypedObject(sourceFiles=[source_managedExecutable], className='managedExecutable', identifierVariables = ['name', 'extension','Path'], objectReferencesDict={}, manager=self),
            polyTypedObject(sourceFiles=[source_polyTypedObjectANDvariables], className='polyTypedObject', identifierVariables = ['className'], objectReferencesDict={self.__class__.__name__:['objectTyping']}, manager=self),
            polyTypedObject(sourceFiles=[source_polyTypedObjectANDvariables], className='polyTypedVariable', identifierVariables = ['name','polyTypedObj'], objectReferencesDict={'polyTypedObject':['polyTypedVars']}, manager=self)
            ]

    #Returns another polyTyped Object instance from the manager object
    def getObject(self, className):
        for obj in self.objectTyping:
            print(obj.className)
            if(obj.className == className):
                return obj
        return None

    def getInstanceIdentifiers(self, instance):
        obj = self.getObject(type(instance).__name__)
        idVars = obj.identifiers
        #Compiles a dictionary of key-value pairs for the identifiers 
        identifiersDict = {}
        for id in idVars:
            identifiersDict[id] = getattr(instance,id)
        listOfIdTuples = identifiersDict.items()
        identifiersTuplified = tuple(listOfIdTuples)
        return identifiersTuplified

    def getInstanceTuple(self, instance):
        return tuple([type(instance).__name__, self.getInstanceIdentifiers(instance), instance])

    def getDuplicateInstanceTuple(self, instance):
        instanceTuple = self.getInstanceTuple(instance)
        path = self.getTuplePathInObjTree(instanceTuple)
        instanceTuple[2] = path
        return instanceTuple

    def makeObjectTree(self, traversalList=None, baseTuple=None):
        print('making tree')
        if(traversalList == None or baseTuple== None):
            baseTuple=tuple([type(self).__name__, self.getInstanceIdentifiers(self), self])
            traversalList=[baseTuple]
            self.objectTree = {baseTuple:{}}
            print('Tree Base Setup, getting Branches.')
        branchingDict = self.getBranches(traversalList)
        print('Got Branches.')
        newBranches = branchingDict['newBranches']
        oldBranches = branchingDict['oldBranches']
        duplicates = branchingDict['duplicates']
        #When a new Branch has had all of it's sub-branches fully flushed out, it will be put
        #into the completeBranches list and removed from the newBranches list.
        completeBranches = []
        #When a duplicate is found, the duplicate and the current 'legitimate' reference will be
        #compared.  If the new duplicate has a branching depth less than the current existing
        #reference, then the new duplicate will replace the original.  After the comparison and
        #potential replacement, the duplicate is removed from duplicates and into accDuplicates
        #or rplDuplicates, if it had replaced a previously existing branch.
        accDuplicates = []
        rplDuplicates = []
        completionCount = 0
        iscomplete = False
        branchPulseComplete = False
        print('before loop')
        while branchPulseComplete == False:
            if(newBranches != []):
                self.addNewBranch(traversalList=traversalList, branchTuple=newBranches[0])
                iscomplete = self.makeObjectTree(traversalList=traversalList+[newBranches[0]], baseTuple=baseTuple)
                if(iscomplete):
                    completionCount += 1
                newBranches.remove(newBranches[0])
            if(oldBranches != []):
                iscomplete = self.makeObjectTree(traversalList=traversalList+[oldBranches[0]], baseTuple=baseTuple)
                if(iscomplete):
                    completionCount += 1
                oldBranches.remove(oldBranches[0])
            if(duplicates != []):
                originalPath = self.getTuplePathInObjTree(instanceTuple=duplicates[0])
                print("originalPath: ")
                print(originalPath)
                print("traversalPath: ")
                print(traversalList)
                #If the newly generated Duplicate has a lower branching depth than the original,
                #then we replace the original with the new path.
                if(len(originalPath) > len(traversalList)):
                    self.replaceOriginalTuple(self, originalPath=originalPath, newPath=traversalList+[duplicates[0]], newTuple=duplicates[0])
                    iscomplete = self.makeObjectTree(traversalList=traversalList+[duplicates[0]], baseTuple=baseTuple)
                    if(iscomplete):
                        completionCount += 1
                    rplDuplicates.append(duplicates[0])
                if(len(originalPath) <= len(traversalList)):
                    self.addDuplicateBranch(traversalList=traversalList, branchTuple=duplicates[0])
                    completionCount += 1
                duplicates.remove(duplicates[0])
            if(newBranches == [] and oldBranches == [] and duplicates == []):
                branchPulseComplete = True
                #If it is the base of the tree, loop runs until all branches are complete.
                #Otherwise, after one branch pulse, everything is returned.
                if(traversalList != [tuple([type(self).__name__, self.getInstanceIdentifiers(self), self])]):
                    return False
                #Check to see if all branches are complete. 
        print('Object Tree: ')
        print(self.objectTree)
        return True
        
        

    #Accesses a branch node and adds a sub-branch to it, if the sub-branch does not already exist.
    def addNewBranch(self, traversalList, branchTuple):
        branchNode = self.getBranchNode(traversalList)
        if(branchNode.get(branchTuple) == None):
            branchNode[branchTuple] = {}

    #Accesses a branch node and adds an empty duplicate sub-branch, which contain identifiers and
    #the path to it's actual branch in the third element of it's tuple.
    def addDuplicateBranch(self, traversalList, branchTuple):
        branchNode = self.getBranchNode(traversalList)
        if(branchNode.get(branchTuple) == None):
            branchNode[branchTuple] = None

    def replaceOriginalTuple(self, originalPath, newPath, newTuple):
        #Get the new branch where this tuple is now going to rest
        newBranch = self.getBranchNode[newPath]
        originalBranch = self.getBranchNode[originalPath]
        originalTuple = None
        for branchTuple in originalBranch.keys():
            if(branchTuple[0]==newTuple[0] and branchTuple[1]==newTuple[1]):
                originalTuple = branchTuple
                break
        #Bring over all of the sub-branches that were attached to it to the new path.
        newBranch[originalTuple] = self.getBranchNode[originalPath+[originalTuple]]
        #Get the original path that the tuple was resting on.
        originalNode = self.getBranchNode[originalPath]
        #Remove the tuple and all of it's sub-branches which have already been moved.
        originalNode.remove(originalTuple)
        #Replace the tuple on the old branch with a 'duplicateTuple' that references the new path.
        replacementTuple = tuple([originalTuple[0], originalTuple[1], originalPath])
        originalNode[replacementTuple] = None

    #Accesses a single object instance and treats it like a branch.
    #This method uses Breadth-first traversal
    def objTreeBranchCreation(self, instanceTuple, traversalList=None):
        if(traversalList==None):
            traversalList=[(type(self).__name__, self.getInstanceIdentifiers(self), self)]
        completeBranch = False
        branchingDepth = len(traversalList)
        branchingDict = self.getBranches(traversalList)
        if(branchingDict["branches"] == []):
            completeBranch = True
        
    #Will go through every dictionary in the object tree and return branching depth of the tuple
    #if the tuple exists within the tree.
    def getTuplePathInObjTree(self, instanceTuple, traversalList=[]):
        if(traversalList==[]):
            print('Trying to find Tuple match in Object Tree for tuple: ')
            print(instanceTuple)
        path = None
        branch = self.getBranchNode(traversalList = traversalList)
        print('Branch to be searched: ')
        print(branch)
        for branchTuple in branch.keys():
            if branchTuple[0] == instanceTuple[0] and branchTuple[1] == instanceTuple[1]:
                if(type(branchTuple[2]) == tuple):
                    print('Found tuple match!')
                    return branchTuple[2]
                print('Found tuple match!')
                print(traversalList)
                return traversalList
        for branchTuple in branch.keys():
            path = self.getTuplePathInObjTree(traversalList=traversalList+[branchTuple],instanceTuple=instanceTuple)
            if(path != None):
                return path
        if(traversalList == []):
            print('Tuple not found in tree!')
        return path

    #Access a single object instance as a node, and checks each typingObject to see what variables
    #that object has which may hold instances of other objects as either a instance or list of
    #instances, then returns all branches seperated into 3 categories "new","old", or "duplicates".
    #new: A branch with this class-identifiers combination does not exist in the tree at all.
    def getBranches(self, traversalList):
        branch = self.getBranchNode(traversalList=traversalList)
        #got branch node
        curTuple = traversalList[len(traversalList)-1]
        #Gets the name for the class of this branch from the tuple.
        classOfBranch = curTuple[0]
        oldBranches = []
        newBranches = []
        branchTuples = []
        duplicateBranchTuples = []
        #Goes through each object type used on the application and creates tuples
        for polyObj in self.objectTyping:
            if classOfBranch in polyObj.objectReferencesDict:
                #In polyObj 'polyObj.className' potential references exist for this object.
                #Here, we get each variable that is a reference or a list of references to a
                #particular type of object.
                for varName in polyObj.objectReferencesDict[classOfBranch]:
                    value = getattr(curTuple[2], varName)
                    if(value == None or value == []):
                        print(varName + ' is an empty variable')
                    elif(type(value) == list):
                        #Adding a list of objects
                        for inst in value:
                            if(type(inst).__name__ == polyObj.className):
                                ids = self.getInstanceIdentifiers(inst)
                                instPath = self.getTuplePathInObjTree(instanceTuple=tuple([polyObj.className, ids, inst]))
                                if instPath == traversalList:
                                    oldBranches.append(tuple([polyObj.className, ids, inst]))
                                if instPath == None:
                                    newBranches.append( tuple([polyObj.className, ids, inst]) )
                                else:
                                    duplicateBranchTuples.append( tuple([polyObj.className, ids, tuple(instPath)]) )
                    else:
                        if(type(value).__name__ == polyObj.className):
                            #Adding one object
                            ids = self.getInstanceIdentifiers(value)
                            valuePath = self.getTuplePathInObjTree(instanceTuple=tuple([polyObj.className, ids, value]))
                            if(valuePath == traversalList):
                                #as an old Branch
                                oldBranches.append( tuple([polyObj.className, ids, value])) 
                            elif(valuePath == None):
                                #as a new Branch
                                newBranches.append( tuple([polyObj.className, ids, value]))
                            else:
                                #as a duplicate branch
                                duplicateBranchTuples.append( tuple([polyObj.className, ids, tuple(valuePath)]) )
        return {"newBranches":newBranches,"oldBranches":oldBranches,"duplicates":duplicateBranchTuples}
        

    def getBranchNode(self, traversalList):
        branch = self.objectTree
        for tup in traversalList:
            branch = branch[tup]
        return branch

    #Creates a User Interface instance for a locally launched application.
    def newlocalUserInterface(self):
        newUI = managedUI()
        newUI.interfaceChannel = dataChannel(name='PolariApp', Path=os.getcwd())

    def shutdown(self):
        self.activeApp = False

    #An application which runs within the it's manager's Event loop, and does not
    #have it's own personal process.
    def managerSyncLoop(self):
        self.lastRequestTime = time.localtime()

    #A single iteration of this application's event loop.
    def eventLoopIteration(self):
        #Go through all subordinate objects for existing remoteEvent and dataRequest
        #objects that have been pulled into python to perform operations on.
        #
        #First, check on the events and data requests located on the immediate app.
        for event in self.eventsToProcess:
            event.processEvent()
        for event in self.eventsToSend:
            if(event.channelType == 'local'):
                (self.localChannel).sendEvent()
            elif(event.channelType == 'closedNetwork'):
                (self.mainChannel).sendEvent()
            else:
                logging.warn(msg='Invalid or Null Channel Type chosen for Event.')
        self.eventsAwaitingResponse
        self.dataStreamsToProcess
        self.dataStreamsToSend
        self.dataStreamsAwaitingResponse
        #Second, check the Application Source Pages and each of their events
        #and data requests.
        if(self.sourcePagesActive != []):
            (self.sourcePagesActive).eventsToProcess
            (self.sourcePagesActive).eventsToSend
            (self.sourcePagesActive).eventsAwaitingResponse
            (self.sourcePagesActive).dataStreamsToProcess
            (self.sourcePagesActive).dataStreamsToSend
            (self.sourcePagesActive).dataStreamsAwaitingResponse
        #Second, checks the Active User Interfaces for pending events and requests
        if(self.UIsActive != []):
            (self.UIsActive).eventsToProcess
            (self.UIsActive).eventsToSend
            (self.UIsActive).eventsAwaitingResponse
            (self.UIsActive).dataStreamsToProcess
            (self.UIsActive).dataStreamsToSend
            (self.UIsActive).dataStreamsAwaitingResponse

    def appLaunch(self):
        self.lastRequestTime = time.localtime()
        #First checks the Main Channel to see if there are any requests there.
        #Note: if the mainChannel is not there, this should not be running.
        now = self.lastRequestTime
        #(Event Loop for the application)
        print('Starting loop at: ' + str(self.lastRequestTime[3]) + ':' + str(self.lastRequestTime[4]))
        while( (now[4] - self.lastRequestTime[4]) < self.timeout):
            now = time.localtime()
        
    def addActiveUI(self, newUserInterface):
        if(newUserInterface.__class__ == 'managedUI'):
            (self.UIsActive).append(newUserInterface)

    def addSourcePage(self, name):
        newSourcePage = browserSourcePage(name=name)
        (self.sourcePages).append()

    def addLaunchPage(self, name):
        newLaunchPage = browserSourcePage(name=name)
        (self.sourcePages).append(newLaunchPage)
        self.landingSourcePage = newLaunchPage

    def launchApp(self):
        if(self.landingSourcePage != None and self.appDB != None and self.mainChannel != None):
            openingPage = (self.landingSourcePage).mainPage

    #Grabs the main data channel and analyzes it first, then goes through all registered sub-channels established by
    #the source pages.  Pulls in operations requests from the individual channels and passes the request to the Manager
    #of the Application.  These operations should then be run through a validation process to ensure they come from
    #the appropriate source and are not an unauthorized command issued to the system(in a later version-currently not built).
    #Certain Pages will only run particular operations repeatedly, and this 
    def runApp(self):
        (self.mainChannel)
        for appPage in self.sourcePages:
            appPage.pageChannel


#A source for a page in browser which is the basis for the Application, of which each client instance has a in-browser
#JSON DB which communicates with the data Channel of it's singular corresponding Application Channel.
class browserSourcePage():
    def __init__(self, name=None, sourceHTMLfile=None, supportFiles=[], supportPages=[]):
        #The base page which is used as a template to generate other pages.
        self.originPage = sourceHTMLfile
        #The JavaScript File which must be referenced to allow the HTML to run for the Polari-Electron App
        self.localSysJS = None
        #The JavaScript File intended for use when using this page over a secure local network.
        self.localNetworkJS = None
        #The main stylesheet used for this page, in css.
        self.stylePage = None
        #The JavaScript file intended for use over the Internet, which must go through multiple
        #security layers to access or change content.
        self.internetPageJS = None
        #Files that are referenced in or conditionally referenced in the Browser Page.
        self.supportFiles = supportFiles
        #browsersourcePage instances which may be linked or referenced or held (as an iFrame 
        #or otherwise) within the Page.
        self.supportPages = supportPages
        #The Data Channel for the overall application this page belongs to.
        self.mainChannel = None
        #The Data Channel meant specifically for this page, meant for optimizing by running functions common to that page
        #in batches, rather than running any general requested action.
        self.pageChannel = None
        #Operations which must be run regularly in order to update the page to reflect data in the database.
        #These Regularly updated sets of data should be 
        self.regularOperations = []
        #Operations that may occur for this page based on user actions (Generated By Client Side Events).
        self.requestOperations = []
        #A Register for Browser Page Instances Registered Directly From The Same System, these pages bypass the regulations
        #which would normally be placed on the code (since the code can be directly edited anyways in that case, normal attacks
        #would be more or less pointless)
        self.localSystemInstanceRegister = []
        #A Register for Browser Page instances on a closed, assumed to be secure network.  Regulations occur as normal on
        #this sort of system, and it can be used for passing information securely between systems without much risk of leaks.
        self.localNetworkInstanceRegister = []
        #A Register for Browser Page Instances open to the public.
        self.publicNetworkInstanceRegister = []

    def loadFromFolder(self, pageFolder):
        if(pageFolder.__class__ == 'managedFolder'):
            if('Complete' in pageFolder.Statuses):
                pageFolder.name
                for someFile in pageFolder.managedFilesActive:
                    if(someFile.name == pageFolder.name):
                        if(someFile.extension == 'html'):
                            self.mainPage = someFile
                        elif(someFile.extension == 'json'):
                            self.pageChannel = someFile
                        else:
                            (self.supportFiles).append(someFile)