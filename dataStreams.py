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
from dataChannels import *
from objectTreeDecorators import *
from managedDB import *
import logging
#An object that sends data out from one data source to many data sinks.
#(A localized API) #Basically -> allows access to active python data in an App or Polari object,
#or data stored in it's Database, if it is not an active object.
#
#If acting on an APP or Polari object as a Sink, actions are intended to be performed server-side
#and will either update or delete data on the App or Polari.
#If an App or Polari is the Source, then data is being pushed from their main server to elsewhere,
#which may be either another App or Polari, or a UI which is sent to the client side if listed
#as the sink.
class dataStream(treeObject):
    #Creates a data request (which may or may not recur) from a single source to many potential
    #sinks.  (Acts as a Junction between managedDB, and managedApps or Polari or Pages)
    
    def __init__(self, source, channels=[], sinkInstances=[], recurring=False):
        print('data stream manager: ', self.manager)
        #The Python Object which connects to the data needing to be sent, serving as the source of this data.
        self.source = source
        #dataChannels that this request should be put into.
        self.channels = channels
        #requests - data that was sent from an external source to one of the servers connected to this dataStream and it's dataChannels.
        self.requests = []
        #A list of responses that have been returned from the channels.
        #This is used to track whether a particular UI as a sink, or a Polari or App server as
        #a sink, has become non-responsive.
        self.responses = []
        #Instances and their classes that this Request needs to put data into.
        self.sinkInstances = []
        #Is this request recurring over a particular time or process interval, or is it one-off?
        self.recurring = recurring
        #What Objects is this dataStream transmitting?  And which of their variables?
        #EX: {Polari: [name, managedApps, hostSystem, isRemote], managedApp: [name, mainChannel]}
        self.objectRequestDict = {}
        #The last time this request had it's information updated.
        self.lastProcessingTime = None
        #The JSON formatted Data, meant for transmitting through dataChannels.
        self.streamJSON = []

    #
    def queueToProcess(self):
        ((self.manager).dataStreamsToProcess).append(self)

    #
    def pushToChannels(self):
        for channel in self.channels:
            channel.pullJSON(self.streamJSON)

    #Accounts for the responses that may have occurred on the dataStream from any of the
    #potential defined sinks
    def reactToResponses(self):
        responsesList = []
        for channel in (self.manager).channels:
            channel
        self.reactToResponse()

    def reactToResponse(self, responseJSON):
        (self.manager)

    def getManagerChannels(self):
        (self.channels).append( (self.manager).localChannel )
        (self.channels).append( (self.manager).mainChannel )

    def getIdData(self, instance):
        #Find PolyTypedObject for the object.
        className = type(instance).__name__
        polyTypingInstance = None
        for polyTypedObj in self.manager.objectTyping:
            if(polyTypedObj.className == className):
                polyTypingInstance = polyTypedObj
        instanceIdentifiers = []
        if(polyTypingInstance != None):
            if(polyTypingInstance.identifiers != []):
                for identifier in (polyTypingInstance.identifiers):
                    #Retrieves the value of the identifier defined and creates a JSON Object for it
                    instanceIdentifiers.append(
                        { identifier : getattr(instance, identifier) }
                    )
        return (className, instanceIdentifiers)

    #Makes the dataStream retrieve all 
    def retrieveDataSet(self, className):
        if(not className in self.objectRequestDict.keys()):
            self.objectRequestDict[className] = '*'
        (sourceClassName, sourceIdentifiers) = self.getIdData(self.source)
        (managerClassName, managerIdentifiers) = self.getIdData(self.manager)
        #Set up the base of the dataSet
        newDataSet = {
            "class":className,
            "manager":(managerClassName, managerIdentifiers),
            "source":(sourceClassName, sourceIdentifiers),
            "sinks":[],
            "data":[
                #Put object instances here.
            ]
        }
        #Write the sinks into the sink section of the base.
        for sinkInstance in self.sinkInstances:
            (sinkClassName, sinkIdentifiers) = self.getIdData(self.manager)
            newDataSet["sinks"].append(
                {
                    "sinkClass":sinkClassName,
                    "sinkIdentifiers":sinkIdentifiers
                }
            )
        #Access the manager and pull data of all objects of the given class.
        instanceSet = self.manager.getListOfClassInstances(className=className, source=self.source)
        #pass the set of all object instances into the function
        newDataSet["data"] = self.getJSONdictForClass(definingFile='dataChannels', className=className, passedInstances=instanceSet)
        (self.streamJSON).append(newDataSet)
        
        
    #Traverses all elements in the manager's object tree, if the class matches this one
    def composeDataStream(self):
        if(source != None):
            if(type(source).__name__ == 'Polari' or type(source).__name__ == 'managedApp'):
                for objName in (self.objectRequestDict).keys():
                    retrieveDataSet(objName)
            else:
                logging.warn(msg='No Source specified for the Data Request!')

    def getActiveData(self, className):
        #
        (self.manager).objectTree

    def retrieveDataInDB(self, dataSet):
        if(source != None):
            if(type(source).__name__ == 'Polari' or type(source).__name__ == 'managedApp'):
                #Retrieve the Database of the source object (same command for both cases)
                sourceDB = (self.source).DB
                sourceDB
            else:
                logging.warn(msg='No Source specified for the Data Request!')

    def storeDataInDB(self):
        #Iterate through all of the dataSets and retrieve which classes are present in it.
        classesDict = {}
        for dataSet in self.streamJSON:
            #Checks if the class already exists in the classes Dictionary.
            #If it does not exist, put the class in as a Key, and assign a list as it's value
            #such that all dataSets of that class can be put into it.
            if(not dataSet['class'] in classesDict):
                classesDict[dataSet['class']] = []
            #Go through all of the Keys in the classesDict and insert all of the values.

    def storeJSONinDB(self):
        self.streamJSON

    #Gets all data for a class and returns a Dictionary which is convertable to a json object.
    def getJSONdictForClass(self, absDirPath = os.path.dirname(os.path.realpath(__file__)),
                        definingFile = os.path.realpath(__file__)[os.path.realpath(__file__).rfind('\\') + 1 : os.path.realpath(__file__).rfind('.')],
                        className = 'testClass', instanceLimit=None, varsLimited=[], passedInstances = None):
        #If an instance or list of instances of the same type are passed, grabs the class name.
        print('passedInstances: ', passedInstances)
        if(passedInstances!=None and passedInstances!=[]):
            if(isinstance(passedInstances, list)):
                className = passedInstances[0].__class__.__name__
            else:
                className = passedInstances.__class__.__name__
        objTyping = None
        for polyTypedObj in self.manager.objectTyping:
            if(polyTypedObj.className == className):
                #print('found object type', polyTypedObj.className)
                objTyping = polyTypedObj
                for someFile in polyTypedObj.sourceFiles:
                    lastSlashIndex = someFile.rfind('\\')
                    #print(lastSlashIndex)
                    someFile = someFile[lastSlashIndex + 1:]
                    print('found and assigning source file: ', someFile)
                    definingFile = someFile
                    break
                #Go through all source files and find the python source file.
                break
        #Gives access to the class by importing it and simultaneously passes in the method for instantiating it.
        returnedClassInstantiationMethod = getAccessToClass(absDirPath, definingFile, className, True)
        classVarDict = [
            {
                "class":className,
                #A limit on the number of objects allowed to be entered into this JSON Dictionary.
                "instanceLimit":instanceLimit,
                #A list of variables which will be excluded from data transmitted for each instance.
                "varsLimited":varsLimited,
                "data":[
                    #Left empty so that instance data can be entered
                ]
            }
        ]
        #dataEntriesList = classVarDict[0]["data"]
        #Accounts for the case where a list of instances of the same class are passed into the function
        if(isinstance(passedInstances, list)):
            for someInstance in passedInstances:
                classInstanceDict = {}
                classInfoDict = someInstance.__dict__
                #print('Printing Class Info: ' + str(classInfoDict))
                for classElement in classInfoDict:
                    if(not callable(classElement) and not classElement in varsLimited):
                        classInstanceDict[classElement] = None
                classVarDict[0]["data"].append( self.getJSONclassInstance(someInstance, classInstanceDict) )
        elif(passedInstances == None):
            if(passedInstances == None):
                classInstance = returnedClassInstantiationMethod()
                classInfoDict = classInstance.__dict__
        else: #Accounts for the case where only a single instance of the class is passed into the function
            classInstanceDict = {}
            classInfoDict = passedInstances.__dict__
            for classElement in classInfoDict:
                #print('got attribute: ' + classElement)
                if(not callable(classElement) and not classElement in varsLimited):
                    classInstanceDict[classElement] = None
                    #print('not callable attribute: ' + classElement)
            classVarDict[0]["data"].append( self.getJSONclassInstance(passedInstances, classInstanceDict) )
        if(instanceLimit != None):
            if( len(classVarDict) > instanceLimit):
                logging.error(msg='Exceeded limit on instances for the dataSet.')
            else:
                print('Class Variable Dictionary: ', classVarDict)
                return classVarDict
        else:
            print('Class Variable Dictionary: ', classVarDict)
            return classVarDict

    #Takes in all information needed to access a class and returns a formatted json string 
    def getJSONforClass(self, absDirPath = os.path.dirname(os.path.realpath(__file__)),
                        definingFile = os.path.realpath(__file__)[os.path.realpath(__file__).rfind('\\') + 1 : os.path.realpath(__file__).rfind('.')],
                        className = 'testClass', passedInstances = None):
        classVarDict = self.getJSONdictForClass(absDirPath=absDirPath,definingFile=definingFile,className=className, passedInstances=passedInstances)
        JSONstring = json.dumps(classVarDict)
        return JSONstring

    

    def getJSONclassInstance(self, passedInstance, classInstanceDict):
        dataTypesPython = ['str','int','float','complex','list','tuple','range','dict','set','frozenset','bool','bytes','bytearray','memoryview', 'NoneType']
        print("entered getJSONclassInstance()")
        for someVariableKey in classInstanceDict.keys():
            #Handles Cases where particular classes must be converted into a string format.
            if(type(getattr(passedInstance, someVariableKey)).__name__ == 'dateTime'):
                classInstanceDict[someVariableKey] = 'someDateTime'
            elif(type(getattr(passedInstance, someVariableKey)).__name__ == 'TextIOWrapper'):
                classInstanceDict[someVariableKey] = 'OpenedFile'
            elif(type(getattr(passedInstance, someVariableKey)).__name__ == 'bytes' or type(getattr(passedInstance, someVariableKey)).__name__ == 'bytearray'):
                #print('found byte var ', someVariableKey, ': ', classInstanceDict[someVariableKey])
                classInstanceDict[someVariableKey] = getattr(passedInstance, someVariableKey).decode()
            elif(ismethod(getattr(passedInstance, someVariableKey))):
                #print('found bound method (not adding this) ', someVariableKey, ': ', getattr(passedInstance, someVariableKey))
                classInstanceDict[someVariableKey] = 'event'
            elif(isclass(type(getattr(passedInstance, someVariableKey))) and not type(getattr(passedInstance, someVariableKey)).__name__ in dataTypesPython):
                #For now just set the value to be the name of the class, will build functionality to put in list of identifiers as a string. Ex: 'ClassName(id0:val0, id1:val1)'
                #print('found custom class or type ', someVariableKey, ': ', getattr(passedInstance, someVariableKey))
                classInstanceDict[someVariableKey] = 'className(id0:val0, id1:val1, ...)'
            #Other cases are cleared, so it is either good or it is unaccounted for so we should let it throw an error.
            else:
                #print('Standard type: ', type(getattr(passedInstance, someVariableKey)))
                classInstanceDict[someVariableKey] = getattr(passedInstance, someVariableKey)
        return classInstanceDict