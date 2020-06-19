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
#as the sink.  To instead update the UI from the UI by-request, a dataStream should be sent
#with the UI as the Source and the App as a Sink, with that UI carrying it's desired update as
#an object instance of itself.
class dataStream():
    #Creates a data request (which may or may not recur) from a single source to many potential
    #sinks.  (Acts as a Junction between managedDB, and managedApps or Polari or Pages)
    def __init__(self, manager=None, source = None, channels=[], sinkInstances=[], recurring=False):
        #The Object (App or Polari) serving as the source of this data.
        self.source = source
        #A unique identifier (Number or Alphanumeric) which is generated for only the purpose
        #to ensure that this dataStream can be uniquely identified in a database.
        self.identifier = None
        if(self.manager == None):
            self.manager = source
        else:
            self.manager = manager
        #dataChannels that this request should be put into.
        self.channels = channels
        #A list of responses that have been returned from the channels.
        #This is used to track whether a particular UI as a sink, or a Polari or App server as
        #a sink, has become non-responsive.
        self.responses = []
        #Instances and their classes that this Request needs to put data into.
        self.sinkInstances = []
        #Is this request recurring over a particular time or process interval, or is it one-off?
        self.recurring = recurring
        #What Objects is this dataRequest transmitting?  And which of their variables?
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
    def process(self):
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

    def sendToChannels(self):
        for channel in self.channels:
            channel.pullJSON(self.streamJSON)

    def getIdData(self, instance):
        #Find PolyTypedObject for the object.
        className = type(instance).__name__
        polyTypingInstance = None
        for polyTypedObj in (instance).objectTyping:
            if(polyTypedObj.name == className):
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

    #First, retrieve all of the active 
    def retrieveDataSet(self, className):
        (sourceClassName, sourceIdentifiers) = self.getIdData(self.source)
        (managerClassName, managerIdentifiers) = self.getIdData(self.manager)
        newDataSet = [{
            "class":className,
            "managerClass":managerClassName,
            "managerIdentifiers":managerIdentifiers,
            "sourceClass":sourceClassName,
            "sourceIdentifiers":sourceIdentifiers,
            "sinks":[],
            "data":[
                #Put object instances here.
            ]
        }]
        for sinkInstance in self.sinkInstances:
            (sinkClassName, sinkIdentifiers) = self.getIdData(self.manager)
            sinkInstance["sinks"].append(
                {
                    "sinkClass":sinkClassName,
                    "sinkIdentifiers":sinkIdentifiers
                }
            )
        
        
    #Traverses all elements in the manager's object tree, if the class matches this one
    def composeDataStram(self):
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