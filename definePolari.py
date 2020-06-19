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
#Polari: An arbitrary name for a collective consciousness that remains native to an isolated machine.
#This logic-based CC is composed of logical concepts based off of Mathematical proofs and concepts
#native to Computer Programming and Computer Hardware Engineering.
#
#The Polari acts as a Hub; which alternates between reading the existing Identities, Concepts, and Memories
#and processing executables / managing Interchange Data, in order to act on those readings or update the
#currently existing logic model while accounting for data seperation needed for optimal execution conditions.
from defineConcepts import Concept
from managedExecutables import managedExecutable
from defineIdentityNode import identityNode
from defineLocalSys import isoSys
from defineLogicNodes import LogicNode
from defineMemories import Mem
from managedApp import *
from managedFiles import managedFile
from managedDB import managedDatabase
from managedFolders import managedFolder
import os, psutil, flask, json, sqlite3, time, webbrowser

#Statuses which are applicable only towards a Polari and adds on to the 'Statuses'
#variable defined in the managedFolder module which are also applicable to this object.

class Polari(managedFolder):
    def __init__(self, name=None, displayName=None, filePath=None, manager=None):
        #Sets up the name for the Polari, which is simultaneously a Directory.
        managedFolder.__init__(self, name=name)
        #Holds the data typing information
        self.objectTyping = []
        #A variable which is used system side to ensure that when connecting across a
        #network, that any Polari with identical names can be uniquely identified.
        self.identifier = None
        #The time, in minutes, where if no events are passed to the Polari, and no
        #events occur in it's sub-polari and Apps, the Polari will shut down.
        self.timeout = 3
        #A dataChannel exposed to other Polari and Applications.
        self.mainChannel = None
        #A dataChannel exposed only to other code running on the local system as a file.
        self.localChannel = None
        #The Directory where the core code for making Polari is held, needed for instantiating new sub-Polari
        self.polariCoreDirectory = None
        #Sets the name that should be displayed to users when they are inspecting this Polari
        self.displayName = displayName
        #A Limit which defines the maximum amount of memory which this Polari should be occupying, if exceeded cease memory operations.
        self.dataOccupationMaximum = None
        #A Limit which will cause the Polari to cease operations if the remaining amount of memory in the system is too small.
        self.memoryRemainingLimit = None
        #Indicates whether or not the Polari is currently active and running.
        self.activePolari = False
        #Holds the information about the Hardware system that this Polari is running on and it's ports.
        self.hostSystem = None
        #Records the overall amount of data occupied by the Polari and all of it's managed resources.
        self.dataConsumption = None
        #Records the number of processes currently being used by the Polari and it's resources.
        self.processConsumption = None
        #Records the number of threads currently being used by the Polari and it's resources.
        self.threadConsumption = None
        #The overall active version of the Polari instance.
        self.version = None
        #The Database utilized by the Polari
        self.DB = None
        #The localized App instance used to manage the Polari, defined as a single Managed App.
        self.polariManagementApp = None
        #The remote method for data entry into the Polari, which may have more restrictions.
        self.polariRemoteManagementApp = None
        #The list of polari that are subordinate to / managed by this Polari.
        #Note: These Polari may be on a remote system and use remoteEvents to correspond.
        self.subPolariInDB = []
        self.subPolariActive = []
        #A list of sub-directory names held in the PolariDirectory, which are effectively managed Apps.
        self.AppsInDB = []
        self.AppsActive = []
        #All of the files under management by this Polari.
        self.managedFilesInDB = []
        self.managedFilesActive = []
        #Images that are being processed or manipulated by the Polari, generally are referenced somewhere within the
        #apps that are managed by it as well and the app is it's final destination when processing is finished.
        self.ImagesInDB = []
        self.ImagesActive = []
        #A list pieces of coding, in any particular language.  These may or may not be in the appropriate file type.
        self.ExecutablesInDB = []
        self.ExecutablesActive = []
        #A list of Logic Node (name, instance) pairs used to compose Memories and Identities
        self.LogicNodesInDB = []
        self.LogicNodesActive = []
        #A list of (Identity Object Instance) Data held Persistantly as named text
        #files, where a single file is managed by a single identity instance.
        #And it's position in accordance with the Executable Dir is recorded.
        self.IdentityNodesInDB = []
        self.IdentityNodesActive = []
        #A list of (Concept Object Instance), where a single file is managed by a single Concept instance.
        self.ConceptsInDB = []
        self.ConceptsActive = []
        #A list of text file names, where a single file is managed by a single Memory instance.
        self.MemoriesInDB = []
        self.MemoriesActive = []
        #Active Events are events that still need operations performed on them
        #by the Polari.  Unresolved Events are events that have been sent from
        #the Polari as a Source and have yet to recieve a response in regards to
        #the result or resolution of that event, or if it was successful.
        self.eventsToProcess = []
        self.eventsToSend = []
        self.eventsAwaitingResponse = []
        self.dataStreamsToProcess = []
        self.dataStreamsToSend = []
        self.dataStreamsAwaitingResponse = []

    def __setattr__(self, key, value):
        #Throw event indicating that the variable was changed
        #WRITE CODE HERE
        #Assign the variable
        super(Point, self).__setattr__(key, value)

    #Pulls in the operations loops of it's active subordinate Applications.
    def polariRun(self):
        self.lastRequestTime = time.localtime()
        #First checks the Main Channel to see if there are any requests there.
        #Note: if the mainChannel is not there, this should not be running.
        now = self.lastRequestTime
        #(Event Loop for the application)
        print('Starting loop at: ' + str(self.lastRequestTime[3]) + ':' + str(self.lastRequestTime[4]))
        while((now[4] - self.lastRequestTime[4]) < self.inactiveTimeout):
            #Checks the time against the timeout
            now = time.localtime()
            if(self.AppsActive != []):
                #Runs one iteration of the event loop for each application.
                for activeApp in self.AppsActive:
                    activeApp.managerSyncLoop()
            if(self.subPolariActive != []):
                #Runs one iteration of the event loop for each application.
                for activePolari in self.subPolariActive:
                    activePolari.managerSyncLoop()

    def addApp(self, newApp):
        if(newApp.__class__ == 'managedApp'):
            (self.AppsActive).append(newApp)        

    #Does validation on the Polari to ensure that everything it needs in order to run has already been prepared before running.
    def metRunRequirements(self):
        self.activePolariLoop = True

    #First checks where the Core Directory is located (where classes used to make a Polari system are defined)
    #Then, checks where the current executable source's Directory is located, in order to account
    #for the saved data from previously used instances of Polari (which should exist in JSON format).
    #Pipelines and Directories used by the previous instance Polari should also exist in the 
    #Executable Directory, and not the Core Directory which is simply used to create object instances.
    def polariInitiation(self):
        #Retrieves the Directory that this class is defined by (Where you are now.)
        polariCoreDirectory = os.path.dirname(os.path.realpath(__file__))
        #Retrieves the Directory of the file that is instantiating the current instance of this class.
        self.filePath = os.path.dirname(psutil.process.exe())
        #Pulls everything in the Class defining directory into a list of text variables.
        initializationDirectory = os.listdir(polariCoreDirectory)
        #Pulls everything in the current same directory as the executable which instantiated this class.
        instantiationDirectory = os.listdir(self.filePath)
        #
        hostSystem = isoSys('UnnamedHostSystem')
        self.hostSystem = ( 'UnnamedHostSystem', hostSystem )
        #Create the Directory which will house everything owned by this Polari
        self.makePolariDefaultApp()

    #Start up Default HTML Browser App and begin to run operations for it's back-end.
    def polariStartup(self):
        PolariManagementApp = "file://" + (self.polariManagementApp).directoryPath + (self.polariManagementApp).Name + '.' + (self.polariManagementApp).extension
        webbrowser.open(PolariManagementApp)
        polariLinearLoop()

    def polariLinearLoop(self):
        while(self.activePolariLoop):
            {
                #Start up Default App and begin to run operations for it's back-end.
            }

    def makePolariDefaultApp(self):
        if(self.exeDirectoryPath != None):
            newPolariApp = managedApp(self.name)
            newPolariApp.setParentDirectoryPath(self.PolariDirectory)

    def getPolariDict(self):
        polariDict = {
        "class":"Polari",
        'data':[
            {
            'name' : self.name,
            'version' : self.version,
            'exeDirectoryPath' : self.exeDirectoryPath,
            'PolariDirectory' : self.PolariDirectory,
            'PolariSaveFile' : self.PolariSaveFile,
            'Apps' : self.getNameList('Apps'),
            'Identities' : self.getNameList('Apps'),
            'Concepts' : self.getNameList('Apps'),   
            'Memories' : self.getNameList('Apps'),
            'Executables' : self.getNameList('Apps'),
            'coreFiles' : self.coreFiles,
            }
        ]
        }
        return polariDict

    #Makes a Database meant to exclusively house data for a single Polari
    def makePolariDB(self):
        if(self.PolariDB == None):
            self.PolariDB = managedDatabase(self.name)
            

    def polariSave(self):
        if(self.PolariSaveFile == None):
            self.PolariSaveFile = managedFile(self.name + '_saveFile_version' + self.version + '.txt')
        polariDict = self.getPolariDict()
        #Opens the save file, deletes all pre-existing data and writes over it.
        with open(self.PolariSaveFile, 'r+') as savefile:
            contents = savefile.read().split("\n")
            savefile.seek(0)
            savefile.truncate()
            json.dumps(polariDict, savefile)


    def polariLoad(self, exeDirectoryPath):
        self.exeDirectoryPath = exeDirectoryPath
        polariCoreDirectory = os.path.dirname(os.path.realpath(__file__))
        #Pulls everything in the Class defining directory into a list of text variables.
        initializationDirectory = os.listdir(polariCoreDirectory)
        #Pulls everything in the current same directory as the executable which instantiated this class.
        instantiationDirectory = os.listdir(self.exeDirectoryPath)
        #
        dataBaseFileList = []
        for anyFileDir in instantiationDirectory:
            if(anyFileDir.find('.db') != -1):
                tempManagedDB = managedDatabase(name=anyFileDir)
                dataBaseFileList.append(tempManagedDB)
        #
        #HERE, WE NEED TO FIND JSON AND DATABASE FILES AND SEE IF ANY CONTAIN A POLARI WITH THIS NAME
        #
        #
        #
        #Here, we loop through the names of everything in the Class's base definition Directory.
        #All we care about in regards to this is that the python files which serve for initialization
        #are accounted for and that their names correspond to our strings in the coreFiles list.
        initFilesAccounted = 0
        for anyFileDir in initializationDirectory :
            if( os.path.isfile(anyFileDir) ):
                if( self.coreFiles.__contains__(os.path.basename(anyFileDir)) ):
                    initFilesAccounted += 1

    def isExpectedFileOrDir(self, something):
        if( os.path.isfile(something) ):
            if(self.Identities.__contains__(os.path.basename(something))):
                return (True, 'File')
            elif( self.Concepts.__contains__(os.path.basename(something)) ):
                return (True, 'File')
            elif( self.Memories.__contains__(os.path.basename(something)) ):
                return (True, 'File')
            elif( self.Executables.__contains__(os.path.basename(something)) ):
                return (True, 'File')
            else:
                return (False, 'File')
        elif( os.path.isdir(something) ):
            if( self.directories.__contains__(os.path.basename(something)) ):
                return (True, 'Directory')
            else:
                return (False, 'Directory')
        else:
            return (False, 'Unknown')