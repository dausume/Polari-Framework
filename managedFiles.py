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
#from functionalityAnalysis import *
#CANNOT DEFINE as @treeObj on managedFile level, causes recursive imports!!
#import objectTreeDecorators
import logging, os
#Centralized global variable arrays accounting for the different types of files/file-extensions the system can handle
#Each individual array accounts for a different type of Object which should be utilized for handling a particular type
#of file.

#Valid file extensions which may be handled using the Generalized managedFile Object.
fileExtensions = ['txt']
#Valid file extensions which may be handled using the managedImage Object
picExtensions = ['svg', 'pil', 'jpg', 'png', 'pdf', 'gif']
#Valid file extensions which may be handled using the managedDB Object
dataBaseExtensions = ['db']
#Valid file extensions which may be handled using the managedDataComms Object
dataCommsExtensions = ['json']
#Valid file extensions which may be handled using the managedExecutable Object
executableExtensions = ['js', 'py', 'html', 'css']

#Wraps the managedFile Object creation and returns the appropriate derivative
#object instance according to the extension.
def fileObject(name=None, Path=None, extension=None):
    tempFileObj = managedFile(name=name, Path=Path, extension=extension, manager=manager)
    if(tempFileObj.extension in fileExtensions):
        fileObj = tempFileObj
    elif(tempFileObj.extension in picExtensions):
        fileObj = tempFileObj.getConvertedFile(definingFile='managedImages', className='managedImage')
    elif(tempFileObj.extension in dataBaseExtensions):
        fileObj = tempFileObj.getConvertedFile(definingFile='managedDB', className='managedDatabase')
    elif(tempFileObj.extension in dataCommsExtensions):
        fileObj = tempFileObj.getConvertedFile(definingFile='dataChannels', className='dataChannel')
    elif(tempFileObj.extension in executableExtensions):
        fileObj = tempFileObj.getConvertedFile(definingFile='managedExecutable', className='managedExecutable')
    return fileObj

#Allows for handling particular file types, and saving them to a register.
#plty is the custom file extension of the Polarity System.
class managedFile:
    
    def __init__(self, name=None, Path=None, extension=None):
        self.name = name
        self.extension = extension
        self.version = None
        #The path to the directory which contains this file.
        self.Path = Path
        #The URL needed to find this file through the internet
        self.url = None
        #Indicates whether this is the active version of this file.
        self.active = False
        #Declares whether this file exists locally, or if a remote data request must be performed to read it's current data.
        self.isRemote = False
        #Indicates whether or not this file actually exists in the OS.
        self.complete = False
        #Shows the last retrieved file size.
        self.fileSize_bytes = None
        #Shows the maximum allowed file size, in bytes, for this file instance.
        self.maxFileSize_bytes = None
        #A variable that holds the Python-defined open file instance, for when the file is opened.
        #This variable, when stored in a database should be converted into a String Base-64 format of the file.
        self.fileInstance = None
        #A boolean variable that says whether or not a given 
        self.isOpen = False
        #Handles where a non-string value is entered, all sub-classes will have their setExtension overwritten and handled.
        if( isinstance(name, str) ):
            dotIndex = name.find('.')
            #Handles the case where a complete filename was entered and parses out it's file extension
            if(dotIndex != -1):
                fileExtension = name[(dotIndex + 1):len(name)]
                self.name = name[0:dotIndex]
                self.setExtension(fileExtension)
            #Handles the case where an extension was directly entered as a parameter.
            elif(extension != None):
                self.name = name
                self.setExtension(extension)
            #Handles the case where neither a filename with an extension or an explicit extension were entered.
            else:
                self.name = name
                #Sets the extension to be txt by default, if it is an actual managedFile object and not a subclass of it.
                if(not issubclass(self.__class__, managedFile)):
                    self.setExtension('txt')
        else:
            logging.exception(msg='An invalid type was entered as the name of the file.')

    #Returns an instance of a class that is a subclass of Folder, with all variables from the
    #Folder instance carried over.
    def getConvertedFile(self, definingFile, className):
        #Gets the default instantiation method for the 
        instMethod = getAccessToClass(absDirPath=self.Path, definingFile=definingFile, className=className, returnMethod=True)
        newInstance = instMethod()
        if(issubclass(newInstance,self)):
            classInfoDict = self.__dict__
            for someVariableKey in classInfoDict.keys():
                if(not callable(someVariableKey)):
                    value = getattr(self, someVariableKey)
                    setattr(newInstance, someVariableKey, value)
            return newInstance
        else:
            logging.warn(msg='Attempted to convert a managedFile into another class which is not it\'s subclass. ')
            return None

    def append(self):
        if(self.fileInstance != None):
            if (self.fileInstance).closed:
                self.openFile()
            (self.fileInstance)

    def exists(self):
        if(os.path.exists(self.name + '.' + self.extension) and self.Path != None):
            return True
        else:
            return False

    #Checks the current size in bytes of the file, and stores it in thr fileSize_bytes variable
    def detectFileSize(self):
        if(os.path.exists(self.name + '.' + self.extension) and self.Path != None):
            self.fileSize_bytes = os.path.getsize(self.Path + '\\' + self.name + '.' + self.extension)
        else:
            logging.error(msg='The directory path of the file must be defined before using this function.')

    def setMaxFileSize(self, maxSize):
        if( isinstance(maxSize, int) ):
            self.maxFileSize_bytes = maxSize

    #So long as a name exists, this will create a file in the system in the defined directory.
    def createFile(self):
        if(not os.path.exists(self.name + '.' + self.extension) and self.name != None):
            if(self.Path == os.getcwd() or self.Path == None):
                self.Path = os.getcwd()
                try:
                    #print('Set path for object ', self, ' to:  ', self.Path)
                    self.fileInstance = open(self.name + '.' + self.extension, mode='x')
                    (self.fileInstance).close()
                except:
                    print('Attempted to create file ', self.name, '.', self.extension, ' but failed, likely file already exists.')
            else:
                logging.warning(msg='Indicated Path lies outside of Current Working Directory, this case is not built out yet.')
        else:
            if(self.Path == None):
                self.Path = os.getcwd()
                logging.warning('Attempting to create a file \'' + self.name + '.' + self.extension + '\' which already exists in the directory, '+ os.getcwd() +'.')
            else:
                logging.warning('Attempting to create a file \'' + self.name + '.' + self.extension + '\' which already exists in the directory, '+ self.Path +'.')

    def openFile(self):
        try:
            if(self.fileInstance != None):
                if(not (self.fileInstance).closed):
                    logging.error(msg='Attempting to open a file Instance that was already opened.')
                else:
                    self.fileInstance = open(self.name + '.' + self.extension,'r+')
            else:
                self.fileInstance = open(self.name + '.' + self.extension,'r+')
        except:
            print('File Instance of file \'', self.name, '.', self.extension, '\' could not be generated.  Either file exists outside of path scope, or it does not exist.')

    def closeFile(self):
        if(not (self.fileInstance).closed):
            (self.fileInstance).close()

    def deleteFile(self):
        if(os.path.exists(self.name + '.' + self.extension)):
            os.remove(self.name + '.' + self.extension)

    def setExtension(self, fileExtension):
        if(fileExtensions.__contains__(fileExtension)):
            self.extension = fileExtension
        elif(picExtensions.__contains__(fileExtension)):
            logging.warning('Entered a valid image file, but instantiated using the wrong object, should be a managedimage.')
        elif(dataBaseExtensions.__contains__(fileExtension)):
            logging.warning('Entered a valid Data Base file, but instantiated using the wrong object, should be a managedDB.')
        elif(dataCommsExtensions.__contains__(fileExtension)):
            logging.warning('Entered a valid file extension meant for data transmissions, but instantiated using the wrong object, should be a dataComms object.')
        elif(executableExtensions.__contains__(fileExtension)):
            logging.warning('Entered an invalid or unhandled file Extension.')
        else:
            logging.warning('Entered an invalid or unhandled file Extension.')

    #Updates the versioning on this file in order to indicate that the AI has changed it in respect to the
    #previously defined versioning.
    def updateAutoVersion(self):
        dotIndex = (self.version).find('.')
        manualVersion = (self.version)[0 : dotIndex - 1]
        autoVersion = (self.version)[dotIndex + 1]
        reverseAutoVersion = ''
        for placeValue in autoVersion:
            reverseAutoVersion = placeValue + reverseAutoVersion
        reverseNewVersion = int(reverseAutoVersion) + 1
        autoVersion = ''
        for placeValue in reverseNewVersion:
            autoVersion = placeValue + autoVersion
        newVersion = manualVersion + '.' + autoVersion

    #Versioning update which takes effect after a User has analyzed System and Deemed it usable
    #This consolidates all automated versioning and records copies of the system as-is at the instant
    #the version is updated.
    def incrementVersion(self):
        dotIndex = (self.version).find('.')
        manualVersion = (self.version)[0 : dotIndex - 1]
        autoVersion = (self.version)[dotIndex + 1]
        newVersion = int(manualVersion) + 1
        self.version = str(newVersion) + '.0'