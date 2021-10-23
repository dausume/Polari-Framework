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
from polariFiles.managedFiles import *
from polariFiles.managedExecutables import *
from polariDBmanagement.managedDB import *
from polariFiles.managedImages import *
from polariFiles.dataChannels import *
from polariAnalytics.functionalityAnalysis import *
import os, shutil
defStatuses = ['Non-Existent','Exists', 'Undefined Files', 'Undefined Sub-Directories', 'Non-Existent Files', 'Non-Existent Sub-Directories', 'Complete', 'Tree-Complete']

class managedFolder():
    def __init__(self, name = None, Path = None, manager=None):
        self.name = name
        self.manager = manager
        #Assigns the manager of this Folder, whether it be a Polari or an Application.
        self.assignManager(manager)
        #The path for this folder, which is used to access all of it's files and sub-folders.
        self.Path = Path
        #The List of file instances or file names that exist within this folder (May or may not exist in actual file system).
        self.managedFiles = []
        #The tree of Directories contained within used to hold data.
        #If this belongs inside of another tree, this will start at the root of that tree.
        #EX: MainORrootDirectory:{WebPageDirectoryName:(webPageDirInstance,{HomePageDirectory, otherPageDirectory}), BackendDirectoryName:(BackendDirectoryInstance,{PythonFunctionDirectory, importsDirectory})}
        self.directoryTree = {}
        #Sub-directories held within this directory.
        self.directories = []
        #A list of statuses indicating to what level the actual file system reflects this object.
        self.Statuses = []
        self.exists()

    #Returns an instance of a class that is a subclass of Folder, with all variables from the
    #Folder instance carried over.
    def getConvertedFolder(self, definingFile, className):
        #Gets the default instantiation method for the 
        instMethod = getAccessToClass(absDirPath=self.Path, definingFile=definingFile, className=className, returnMethod=True)
        newInstance = instMethod()
        classInfoDict = self.__dict__
        for someVariableKey in classInfoDict.keys():
            if(not callable(someVariableKey)):
                value = getattr(self, someVariableKey)
                setattr(newInstance, someVariableKey, value)
        return newInstance

    #Builds the tree and then distributes copies of the Tree to all of it's Folders inside of it.
    def buildTree(self):
        self.directoryTree = self.makeTree()
        self.distributeTree(self.directoryTree,pathList=[self.name])

    def getFilesInTree(self, pathList=[], filesList=[], extensions=None):
        if(extensions==None):
            for someFile in self.getHardFiles():
                newFile = managedFile(name=someFile)
                newFile.Path = self.Path
                filesList.append(newFile)
            filesList.append()
        elif(type(extensions).__name__ == list):
            for fileName in self.getHardFiles():
                #Put the file in the List if it is in the hardfiles and has one of the extensions.
                for extension in extensions:
                    if fileName.__contains__('.' + extension):
                        newFile = managedFile(name=someFile)
                        newFile.Path = self.Path
                        filesList.append(newFile)
                        break
        #At this point all files meeting the criteria from this directory have been added.
        curBranch = self.directoryTree
        #Traverse the tree using the pathList which holds in-sequence keys to access the cur branch.
        for key in pathList:
            curBranch = curBranch[key]
        curBranch = curBranch[self.name]
        haveNotBeen = curBranch.keys()
        haveBeen = []
        pathList.append(self.name)
        for dirName in haveNotBeen:
            filesList.extend( curBranch[dirName][0].getFilesInTree(pathList=pathList,extensions=extensions) )
        return filesList

    #Recursively accesses every folder in the tree and passes the entire tree into it.
    def distributeTree(self, tree, pathList):
        #There will always be one Directory acting as the base, so we just get it's name.
        self.directoryTree = tree
        curBranch = tree
        #Traverse the tree using the pathList which holds in-sequence keys to access the cur branch.
        for key in pathList:
            curBranch = curBranch[key]
        curBranch = curBranch[self.name]
        haveNotBeen = curBranch.keys()
        haveBeen = []
        pathList.append(self.name)
        #Call the recursive function for each subdirectory on a given level
        for dirName in haveNotBeen:
            curBranch[dirName][0].distributeTree(tree=tree,pathList=pathList)
        return

    #Recursively calls itself until the all branches are accounted for.
    def makeTree(self):
        #There will always be one Directory acting as the base, so we just get it's name.
        haveNotBeen = self.getHardDirs()
        haveBeen = []
        treeBranch = {self.name:[self,{}]}
        #Call the recursive function for each subdirectory on a given level
        for dirName in haveNotBeen:
            newDir = managedFolder(name=dirName)
            newDir.Path = self.Path + '/' + self.name + '/'
            (self.directoriesActive).append(newDir)
            haveBeen.append(newDir.makeTree())
            #For each of the branches passed back, add a new key-value pair onto this branch
            #Then, return this branch.
        for dirBranch in haveBeen:
            branchKey = dirBranch.keys()[0]
            (treeBranch[self.name][1])[branchKey] = [dirBranch[branchKey][0],dirBranch[branchKey][1]]
        return treeBranch

    def detectStatuses(self, wrappedFunc):
        def innerFunc(self):
            #Detects whether or not the Directory itself exists accurately in the file system
            if(self.filePath != None and self.name != None):
                if(os.path.exists(self.filePath + self.name)):
                    if((self.Statuses).__contains__('Non-Existent')):
                        (self.Statuses).remove('Non-Existent')
                    (self.Statuses).append('Exists')
                else:
                    if((self.Statuses).__contains__('Exists')):
                        (self.Statuses).remove('Exists')
                    (self.dirStatus).append('Non-Existent')
            #Based on the previous result, continues on to see if the files and sub-directories python-side
            #are accurately reflected.
            if((self.Statuses).__contains__('Exists')):
                for someDir in self.directoriesActive:
                    if(not someDir.exists()):
                        (self.dirStatus).append('Non-Existent Sub-Directories')
                for someDirName in self.directoriesInDB:
                    if(not os.path.exists(someDirName)):
                        (self.dirStatus).append('Non-Existent Sub-Directories')
                for someFile in self.managedFilesActive:
                    if(not someFile.exists()):
                        (self.dirStatus).append('Non-Existent Files')
                for someFileName in self.managedFilesInDB:
                    if(os.path.exists(someFileName)):
                        (self.dirStatus).append('Non-Existent Files')
                hardFiles = self.getHardFiles()
                hardDirs = self.getHardDirs()
                #Goes through each hard file and hard directory found in the system directory and compares them to the
                #defined files in python.
                for hardFileName in hardFiles:
                    foundMatch = False
                    for someFile in self.managedFilesActive:
                        if(someFile.name + '.' + someFile.extension == hardFileName):
                            foundMatch = True
                            break
                    for someFileName in self.managedFilesInDB:
                        if(someFileName == hardFileName):
                            founmatch = True
                    if(not foundMatch):
                        (self.dirStatus).append('Undefined Files')
                for hardDirName in hardDirs:
                    foundMatch = False
                    for someDir in self.directoriesActive:
                        if(someDir.name == hardDirName):
                            foundMatch = True
                            break
                    for someDir in self.directoriesInDB:
                        if(someDir == hardDirName):
                            foundMatch = True
                    if(not foundMatch):
                        (self.dirStatus).append('Undefined Sub-Directories')
                #Checks to make sure that the files and Directories on both on the Python and File System sides.
                if( (self.Statuses).__contains__('Undefined Files'),
                    (self.Statuses).__contains__('Undefined Sub-Directories'),
                    (self.Statuses).__contains__('Non-Existent Files'),
                    (self.Statuses).__contains__('Non-Existent Sub-Directories')):
                    (self.Statuses).append('Complete')


    def exists(self):
        if(self.Path != None and self.name != None):
            if(os.path.exists(self.Path + self.name)):
                return True
        return False

    def loadAllFromSys(self):
        if(self.exists()):
            self.loadDirsFromSys()
            self.loadFilesFromSys()

    def loadDirsFromSys(self):
        if(self.exists()):
            subDirsList = getHardDirs()
            for hardDir in subDirsList:
                continue

    def loadFilesFromSys(self):
        if(self.exists()):
            filesList = getHardFiles()
            return

    #Returns the list of actual files stored in this directory
    def getHardFiles(self):
        hardFiles = None
        if(self.exists()):
            i=0
            filesOrDirs = os.listdir(self.filePath + '/' + self.name)
            hardFiles = []
            for fileOrDir in filesOrDirs:
                if(os.path.isfile(fileOrDir)):
                    hardFiles.append(fileOrDir)
        return hardFiles
        
    #Returns the list of actual directories stored in this directory
    def getHardDirs(self):
        hardDirs = None
        if(self.exists()):
            i=0
            filesOrDirs = os.listdir(self.filePath + '/' + self.name)
            hardDirs = []
            for fileOrDir in filesOrDirs:
                if(os.path.isdir(fileOrDir)):
                    hardDirs.append(fileOrDir)
        return hardDirs

    def assignManager(self, manager):
        if(manager.__class__ == 'managedApp' or manager.__class__ == 'Polari'):
            self.manager = manager
        elif(manager == None):
            return

    #Creates the actual directory in the file system according to the information defined in the managedFolder object.
    def mkDir(self):
        if(self.Path == None):
            self.Path = os.getcwd()
        dirPath = self.Path + '/' + self.name
        if(not os.path.exists(self.Path)):
            os.mkdir(dirPath)
        self.exists()

    def delete(self):
        shutil.rmtree()

    def makeFile(self, name=None, extension=None):
        if extension in fileExtensions:
            newFile = managedFile(name=name, extension=extension)
        elif extension in picExtensions:
            newFile = managedImage(name=name, extension=extension)
        elif extension in dataBaseExtensions:
            newFile = managedDatabase(name=name)
        elif extension in dataCommsExtensions:
            newFile = dataChannel(name=name)
        elif extension in executableExtensions:
            newFile = managedExecutable(name=name, extension=extension)
        newFile.Path = self.Path + '/' + self.name
        newFile.createFile()
        (self.managedFiles).append(newFile)

    def makeSubDirectory(self, newDirName):
        newDir = managedFolder.__init__(newDirName, filePath=(self.filePath + '/' + self.name))
        (self.directoryTreeActive).append(newDir)

    #Returns whether an obejct is in the App's Database.
    def isInAppDB(self, name, className):
        if name in self.managedFilesInDB:
            return True
        else:
            return False

    def getActiveFile(self, name, extension):
        for someFile in self.managedFiles:
            if(someFile.name == name):
                return someFile
        return None