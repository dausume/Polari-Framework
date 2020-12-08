#A file that holds functions that are useful for transferring data... and a Class for files that does so too.
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
from functionalityAnalysis import getAccessToClass
from inspect import isclass, ismethod
from managedFiles import *
from objectTreeDecorators import *
import os, json, logging, datetime

#A file used to manage JSON for a particular Polari or App.
class dataChannel(managedFile, treeObject):
    @treeObjectInit
    def __init__(self, manager, name=None, Path=None):
        managedFile.__init__(self, name=name, extension='json')
        #The JSON currently being manipulated in the python object
        self.jsonDict = []
        #The recorded JSON from the last time the JSON File was read.
        self.lastFileReadJSON = []
        #The current system performing operations on the file, according to last reading.
        #Ex: (sourceClass:Polari, sourceName:polariName)
        if(manager == None):
            self.currentOwner = (None, None)
        else:
            self.currentOwner = (manager.__class__.__name__, manager.getInstanceIdentifiers(instance=manager))
        #Register for the different Sources "(managerClass, manager's Id Tuple): { 'objectName':( [Scope Limiter 'a query or filter'], ['get', 'put', 'post', 'delete', 'auth']) }"
        #which specifies what data is to be pulled into this JSON File, auth means that a specific object is searched for and if it is found with matching identifiers,
        #the data goes through.
        self.localSourceRegister = {self.currentOwner:{}}
        self.remoteSourceRegister = {}
        #Register for the different Sinks which consume data from this JSON File, and their access order.
        #Ex: ( self.currentOwner, { "user":"*" } ) would mean the dataChannel allows for anyone with access to it
        self.localSinkRegister = {self.currentOwner:{}}
        self.remoteSinkRegister = {}
        #The date-time when the last source claimed ownership of the JSON File.
        self.lastRefreshDateTime = None
        print('jsonDict at dataChannel ', self.name, ' initialization before makeChannel: ', self.jsonDict)
        self.makeChannel()
        print('jsonDict at dataChannel ', self.name, ' initialization after makeChannel.', self.jsonDict)

    def makeChannel(self):
        self.createFile()
        #os.path.basename(__file__)
        dataChannelBase = self.makeDataSet(className="dataChannel")
        self.jsonDict.append(dataChannelBase)
        #self.getJSONdictForClass(definingFile='dataChannels', className=self.__class__.__name__,passedInstances=[self], instanceLimit=1, varsLimited=['lastFileReadJSON', 'jsonDict', 'fileInstance'])
        # Serialize json
        print('Printing dataChannel Base in the makeChannel function: ',dataChannelBase)
        jsonStr = json.dumps(dataChannelBase)
        # Write to the dataChannel
        with open(self.name + '.json', "w") as outfile: 
            outfile.write(jsonStr)

    #The function called by an App or Polari when it looks through the dataChannel for requests
    #intended for itself.
    def channelIteration(self):
        available = self.checkChannelAvailability()

    def retrieveDataSet(self, className, source=None):
        #print("Retrieving a data set")
        (managerClassName, managerIdentifiers) = self.getIdData(self.manager)
        if(source == None):
            (sourceClassName, sourceIdentifiers) = (managerClassName, managerIdentifiers)
        else:
            (sourceClassName, sourceIdentifiers) = self.getIdData(source)
        for someDataSet in self.jsonDict:
            #print('In retrieveDataSet, printing the current data set: ', someDataSet)
            if(someDataSet != None):
                if("class" in someDataSet and "manager"  in someDataSet and "source"  in someDataSet):
                    if(someDataSet["class"] == className and someDataSet["manager"] == (managerClassName, managerIdentifiers) and someDataSet["source"] == (sourceClassName, sourceIdentifiers)):
                        #print("Successfully returning Data Set")
                        return someDataSet
                else:
                    print("!! WARNING: Data Set was missing class, manager, or source specifications !!")
            else:
                self.jsonDict.remove(someDataSet)
        return None

    def updateDataSet(self, className, source=None, filter="*", sinks=[]):
        #Find if the data set already exists
        updatingDataSet = self.retrieveDataSet(className, source)
        if(updatingDataSet != None):
            #Access the manager and pull data of all objects of the given class.
            instanceSet = self.manager.getListOfClassInstances(className=className, source=self.manager)
            #print('In update dataSet')
            setToUpload = self.getJSONdictForClass(definingFile='dataChannels', className=className, passedInstances=instanceSet)
        else:
            print('The data set you are attempting to update with values: Class Name = ', className, ', Source = ', source, ', Filter = ', filter, ' does not exist.')

    #Either updates a dataSet or inserts a new dataset
    def makeDataSet(self, className, source=None, filter="*", sinks=[], instances=[]):
        (managerClassName, managerIdentifiers) = self.getIdData(self.manager)
        if(source == None):
            (sourceClassName, sourceIdentifiers) = (managerClassName, managerIdentifiers)
        else:
            (sourceClassName, sourceIdentifiers) = self.getIdData(source)
        #Make sure the dataSet does not already exist before creating and adding it to the dataChannel.
        if( self.retrieveDataSet(className=className, source=source) != None ):
            #print("Attempting to create a dataSet that already exists with values: Class Name = ", className, ', Source = ', source, ', Filter = ', filter, '.')
            self.updateDataSet(className=className, source=source, filter=filter, sinks=sinks)
        else:
            #Set up the base of the dataSet, there will be one dataSet per source-manager per object accounted for.
            #Note: Manager objects may hold object instances within them that have a remote source-manager object, in this case where the source and manager object are different,
            #it means that the object is read-only on the given manager object and a re-direct must be performed for any commands that are not 'get' or 'auth'.
            newDataSet = {
                "class":className,
                "manager":(managerClassName, managerIdentifiers),
                "source":(sourceClassName, sourceIdentifiers),
                "create":False,
                "delete":False,
                #If true, all fields/variables from this class are sent/readable for instances in this dataSet.
                "readAll":True,
                #For cases with readAll == False, the list of readable fields/variables for instances in this dataSet
                "readSpecifics":[

                ],
                "updateAll":False,
                "updateSpecifics":[

                ],
                "functionsAll":False,
                "functionsSpecifics":[
                    
                ],
                "filter":filter,
                "sinks":[],
                "data":[
                    #Put object instances here.
                ]
            }
            #Write the sinks into the sink section of the base.
            for sinkInstance in self.localSinkRegister:
                (sinkClassName, sinkIdentifiers) = self.getIdData(self.manager)
                newDataSet["sinks"].append(
                    {
                        "sinkClass":sinkClassName,
                        "sinkIdentifiers":sinkIdentifiers
                    }
                )
            #Access the manager and pull data of all objects of the given class.
            instanceSet = self.manager.getListOfClassInstances(className=className, source=self.manager)
            print("List of instances returned: ", instanceSet)
            #print('In makeDataSet, defining dataSet for class: ', className)
            #print('instanceSet being passed: ', instanceSet)
            #pass the set of all object instances into the function
            defFileObj = self.manager.getObjectTypingClassFile(className=className)
            if(instanceSet != []):
                newDataSet["data"] = self.getJSONdictForClass(definingFile=defFileObj.name, className=className, passedInstances=instanceSet)
            (self.jsonDict).append(newDataSet)
            #print("Made new dataSet: ", newDataSet)
            #print("Channel's jsondict after appending new dataSet: ", self.jsonDict)

    #Injects all JSON currently in the jsonDict variable, into the JSON file.
    def injectJSON(self):
        #if(self.checkChannelAvailability()):
        #self.openChannel()
        self.openFile()
        print(self.fileInstance)
        #Dumps the jsonDict variable into the dataChannel file.
        json.dump(
            self.jsonDict,
            self.fileInstance
        )
        self.closeFile()

    #Goes through all access records in the JSON file, and returns True if this Object currently owns the writing access
    #to the channel or if nothing owns the writing access currently.  Returns False if writing access is currently owned
    #by another party.
    def checkChannelAvailability(self):
        isAvailable = True
        self.openFile()
        print(self.Path, '/', self.name, '.', self.extension)
        if(not os.stat(self.Path + '/' + self.name + '.' + self.extension)):
            self.lastFileReadJSON = json.load(self.fileInstance)
        self.closeFile()
        accessDataSets = self.getClassDataSets('dataChannel')
        #print('Access Data Sets: ', accessDataSets)
        setIndex = 0
        occupationIndex = None
        lastOccupationDateTime = None
        for dataSet in accessDataSets[1]:
            #print('In a dataSet: ', dataSet)
            if(lastOccupationDateTime != None):
                #If the occupationDateTime of this dataSet is more recent than the current 'lastOccupationDateTime', set it.
                if((dataSet.get('occupationDateTime') - lastOccupationDateTime) > 0):
                    lastOccupationDateTime = dataSet.get('occupationDateTime')
                    occupationIndex = setIndex
            else:
                lastOccupationDateTime = dataSet.get('occupationDateTime')
                occupationIndex = setIndex
            setIndex += 1
        if(occupationIndex != None):
            lastAccess = accessDataSets[occupationIndex]
            #If the current 'manager' is not the most recent occupant of the File, and there is another occupant, it is not available.
            if(lastAccess.get('currentOwner') != (str(type(self.manager).__name__), (self.manager).name) and lastAccess.get('currentOwner') != (None, None)):
                isAvailable = False
        self.lastOccupationDateTime = lastOccupationDateTime
        return isAvailable

    #Checks the channel asynchronously to see if it is available, if it is, then we claim it and do operations as needed.
    #def occupyChannel(self):
        #open the file
        #self.openFile()
        #If we successfully open the file, pull information from there.
        #if(self.checkChannelAvailability()):
            #If file is opened, and we detect that the file does not have another Owner acting on it currently, and we claim it.
            #self.currentOwner = ((self.manager).__class__, (self.manager).name)
            #self.occupationDateTime = datetime.datetime.now()
            #json.dump(
            #    getJSONdictForClass(definingFile='dataChannels', className='dataChannel', passedInstances=self),
            #    self.fileInstance
            #)

    def openChannel(self):
        #If we successfully open the file, and make sure it is owned by this dataChannel object.
        #if(self.checkChannelAvailability()):
        #open the file
        self.openFile()
        #If file is opened, and we detect that the file does not have another Owner acting on it currently, and we claim it.
        self.currentOwner = (None, None)
        print(self.fileInstance)
        print(self.getJSONdictForClass(definingFile='dataChannels', className='dataChannel', passedInstances=self))
        json.dump(
            self.getJSONdictForClass(definingFile='dataChannels', className='dataChannel', passedInstances=self),
            self.fileInstance
        )

    def setExtension(self, fileExtension):
        if(fileExtensions.__contains__(fileExtension)):
            logging.warning('Entered a valid file extension, but instantiated using the wrong object, should be a managedFile.')
        elif(picExtensions.__contains__(fileExtension)):
            logging.warning('Entered a valid image file, but instantiated using the wrong object, should be a managedimage.')
        elif(dataBaseExtensions.__contains__(fileExtension)):
            logging.warning('Entered a valid Data Base file, but instantiated using the wrong object, should be a managedDB.')
        elif(dataCommsExtensions.__contains__(fileExtension)):
            self.extension = fileExtension
        elif(executableExtensions.__contains__(fileExtension)):
            logging.warning('Entered an invalid or unhandled file Extension.')
        else:
            logging.warning('Entered an invalid or unhandled file Extension.')

    def claimAccess(self, sourceClass, sourceName):
       self.lastInputTuple = (sourceClass, sourceName)

    def addMetaData(self, metaTupleList):
        for dataSet in self.jsonDict:
            for metaTuple in metaTupleList:
                if metaTuple[0] != 'name' and metaTuple[0] != 'class':
                    dataSet[metaTuple[0]] = metaTuple[1]

    #varsToReturn - Defines variables that will be retrieved from each instance retrieved.
    #varQuery - Narrows down the search for instances to be retrieved to those with specific variable values.
    #metaQuery - Narrows down the dataSets to be retrieved from using metaData about the dataSets.
    #classQuery - Narrows down the dataSets to be retrieved to strictly one class.
    #Returns a JSON Dict that has narrowed down or eliminated all unncessary data.
    def queryJSON(self, varsToReturn = None, varQuery = None, metaQuery = None, classQuery = None):
        jsonQueried = self.jsonDict
        #If a String is entered, this string should be a singular class name.
        #The entry of this string should eliminate any dataSets that do not have this class as their metadata.
        if(classQuery != None):
            indexAry = []
            dataSetIndex = 0
            #Go through each dataSet, if it does not match the class, add it to the list of indexed sets to be deleted.
            for dataSet in jsonQueried:
                if not 'class' in dataSet.keys():
                    indexAry.append(dataSetIndex)
                elif(dataSet.get('class') != classQuery):
                    indexAry.append(dataSetIndex)
                dataSetIndex += 1
            iter = 0
            #Go through each indexed Query, as each is removed, the indexes must be decrimented by 1 to remain pointing
            #at the correct locations.
            for i in indexAry:
                del jsonQueried[i - iter]
                iter += 1
        #A metaQuery is expected to be a list of tuples, where each tuple is a key-value pair being queried for.
        if(metaQuery != None):
            indexAry = []
            dataSetIndex = 0
            #Go through each dataSet, if all metaData tuples are not a match, add it to the list of indexed sets to be deleted.
            for dataSet in jsonQueried:
                metaIndex = 0
                for metaTuple in metaQuery:
                    if metaTuple[0] in dataSet.keys():
                        if dataSet.get(metaTuple[0]) == metaTuple[1]:
                            continue
                        else:
                            indexAry.append(dataSetIndex)
                            break
                    else:
                        indexAry.append(dataSetIndex)
                        break
                dataSetIndex += 1
            iter = 0
            #Go through each indexed Query, as each is removed, the indexes must be decrimented by 1 to remain pointing
            #at the correct locations.
            for i in indexAry:
                del jsonQueried[i - iter]
                iter += 1
        #Goes through all instances in remaining dataSets and eliminates them if the varQueried Tuples do not match.
        if(varQuery != None):
            for dataSet in jsonQueried:
                indexAry = 0
                instanceIndex = 0
                for instance in dataSet.get('data'):
                    for varQueryTuple in varQuery:
                        if varQueryTuple[0] in instance.keys():
                            if instance.get(varQueryTuple[0]) == varQueryTuple[1]:
                                continue
                            else:
                                indexAry.append(instanceIndex)
                                break
                        else:
                            indexAry.append(instanceIndex)
                            break
                    instanceIndex += 1
                #Go through each indexed Query, as each is removed, the indexes must be decrimented by 1 to remain pointing
                #at the correct locations.
                for i in indexAry:
                    del dataSet.get('data')[i - iter]
                    iter += 1
        #Removes all non-requested variables from instances.
        if(varsToReturn != None):
            for dataSet in jsonQueried:
                keyAry = []
                instanceIndex = 0
                for instance in dataSet.get('data'):
                    keyAry = []
                    for Var in instance.keys():
                        if not Var in varsToReturn:
                            keyAry.append(Var)
                    instanceIndex += 1
                #Go through each indexed Query, as each is removed, the indexes must be decrimented by 1 to remain pointing
                #at the correct locations.
                for i in indexAry:
                    del dataSet.get('data')[i - iter]
                    iter += 1

    #Takes a Polari Formatted JSON dataSet and pulls all of it's data Sets into this JSON instance.
    def pullJSON(self, otherSet):
        if(isinstance(otherSet, list)):
            for newDataSet in otherSet:
                duplicationDataSetTuple = self.hasDuplicateDataSet(newDataSet)
                if(duplicationDataSetTuple[0]): #A duplicate data set was found.
                    #Iterates through each instance in the dataSet which was found to be the duplicate of the new dataSet
                    instanceIndex = 0
                    duplicateTuples = self.matchDuplicateInstances()
                    isDuplicate = False
                    for newInstance in newDataSet:
                        #Go through all of the duplicate tuples and see if the second value matches
                        for dupTuple in duplicateTuples:
                            if(dupTuple[1] == instanceIndex):
                                isDuplicate = True
                        if(not isDuplicate):
                            duplicationDataSetTuple[1].append(newInstance)
                        instanceIndex += 1
                else: #There is no duplicate DataSet.
                    (self.jsonDict).append(newDataSet)

    #Returns a list of tuples that maps the indexes of duplicates from the stored dataSet to the new dataSet.
    #Ex: duplicatePairsList = [(3,4),(5,8)] means two duplicates were found, if one were to pull all info from the new
    #data set, they would exclude pulling indexes 4 & 8 since they already exist at indexes 3 & 5.
    def matchDuplicateInstances(self, dataSetIndex, duplicateDataSet):
        instanceIndex = 0
        newInstanceIndex = 0
        duplicatePairsList = []
        #Iterates through each instance in the matched Duplicate Data Set of this object's JSON Dictionary.
        for instance in (self.jsonDict[dataSetIndex]).get('data'):
            newInstanceIndex = 0
            #Iterates through each instance in the matched Duplicate Data Set of the new JSON Dictionary.
            for newInstance in duplicateDataSet.get('data'):
                #Iterates through the keys of a particular instance in the new Data Set and compares them to the instance.
                keysMatched = 0
                for key in newInstance.keys():
                    if(instance.get(key) == newInstance.get(key)):
                        keysMatched += 1
                    else:
                        break
                #Checks to see if this new instance was a duplicate of the instance currently being iterated.
                if(keysMatched == len(instance.keys())):
                    duplicatePairsList.append( (instanceIndex, newInstanceIndex) )
                    break
                else:
                    newInstanceIndex += 1
            instanceIndex += 1
        return duplicatePairsList

    #Takes in a new potential JSON dataSet and compares it to all existing dataSets, to ensure there are no duplicates
    def hasDuplicateDataSet(self, newDataSet):
        hasDuplicate = False
        duplicateIndex = 0
        keysMatched = 0
        for dataSet in self.jsonDict:
            keysMatched = 0
            for key in dataSet:
                if(newDataSet.keys().__contains__(key)):
                    if(dataSet.get(key) == newDataSet.get(key) or key == 'data'):
                        keysMatched += 1
                    else:
                        break
                else:
                    break
            if(len(dataSet.keys()) == keysMatched):
                hasDuplicate = True
                break
            else:
                duplicateIndex += 1
        return (hasDuplicate, duplicateIndex)

    def getClassDataSets(self, className):
        tempDict = []
        foundSet = False
        if(self.jsonDict != [] and self.jsonDict != None):
            for dataSet in (self.jsonDict):
                if(dataSet != None):
                    if(dataSet.keys()).__contains__('class'):
                        if(dataSet.get('class') == className):
                            tempDict.append(dataSet)
                            foundSet = True
            if(not foundSet):
                logging.warning(msg='No Class Instances found in JSON Dict.')
        else:
            logging.error(msg='JSON Data must first be entered before any info can be extracted.')
        return (foundSet, tempDict)

    #Gets all data for a class and returns a Dictionary which is convertable to a json object.
    def getJSONdictForClass(self, absDirPath = os.path.dirname(os.path.realpath(__file__)),
                        definingFile = os.path.realpath(__file__)[os.path.realpath(__file__).rfind('\\') + 1 : os.path.realpath(__file__).rfind('.')],
                        className = 'testClass', instanceLimit=None, varsLimited=[], passedInstances = None):
        #If an instance or list of instances of the same type are passed, grabs the class name.
        if(passedInstances!=None):
            if(isinstance(passedInstances, list)):
                if(passedInstances != []):
                    className = passedInstances[0].__class__.__name__
                else:
                    className = passedInstances.__class__.__name__
            else:
                className = passedInstances.__class__.__name__
        #Gives access to the class by importing it and simultaneously passes in the method for instantiating it.
        #returnedClassInstantiationMethod = getAccessToClass(absDirPath, definingFile, className, True)
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
                #classInstance = returnedClassInstantiationMethod()
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
                #print('Class Variable Dictionary: ', classVarDict)
                return classVarDict
        else:
            #print('Class Variable Dictionary: ', classVarDict)
            return classVarDict

    #Takes in all information needed to access a class and returns a formatted json string 
    def getJSONforClass(self, absDirPath = os.path.dirname(os.path.realpath(__file__)),
                        definingFile = os.path.realpath(__file__)[os.path.realpath(__file__).rfind('\\') + 1 : os.path.realpath(__file__).rfind('.')],
                        className = 'testClass', passedInstances = None):
        classVarDict = self.getJSONdictForClass(absDirPath=absDirPath,definingFile=definingFile,className=className, passedInstances=passedInstances)
        JSONstring = json.dumps(classVarDict)
        return JSONstring

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

    

    #Traverses all elements in the manager's object tree, if the class matches this one
    #def composeDataStream(self):
    #    if(source != None):
    #        if(type(source).__name__ == 'Polari' or type(source).__name__ == 'managedApp'):
    #            for objName in (self.objectRequestDict).keys():
    #                retrieveDataSet(objName)
    #        else:
    #            logging.warn(msg='No Source specified for the Data Request!')

    def getActiveData(self, className):
        #
        (self.manager).objectTree

    def getJSONclassInstance(self, passedInstance, classInstanceDict):
        dataTypesPython = ['str','int','float','complex','list','tuple','range','dict','set','frozenset','bool','bytes','bytearray','memoryview', 'NoneType']
        print("entered getJSONclassInstance()")
        for someVariableKey in classInstanceDict.keys():
            #Handles Cases where particular classes must be converted into a string format.
            if(type(getattr(passedInstance, someVariableKey)).__name__ == 'dateTime'):
                classInstanceDict[someVariableKey] = "someDateTime"
            elif(type(getattr(passedInstance, someVariableKey)).__name__ == 'TextIOWrapper'):
                classInstanceDict[someVariableKey] = "OpenedFile"
            elif(type(getattr(passedInstance, someVariableKey)).__name__ == 'bytes' or type(getattr(passedInstance, someVariableKey)).__name__ == 'bytearray'):
                #print('found byte var ', someVariableKey, ': ', classInstanceDict[someVariableKey])
                classInstanceDict[someVariableKey] = getattr(passedInstance, someVariableKey).decode()
            elif(type(getattr(passedInstance, someVariableKey)).__name__ == 'dict'):
                classInstanceDict[someVariableKey] = 'Some dict'
            elif(type(getattr(passedInstance, someVariableKey)).__name__ == 'tuple' or type(getattr(passedInstance, someVariableKey)).__name__ == 'list'):
                #print('found byte var ', someVariableKey, ': ', classInstanceDict[someVariableKey])
                classInstanceDict[someVariableKey] = self.convertTupleOrListToJSONdict(passedSet=getattr(passedInstance, someVariableKey))
            elif(ismethod(getattr(passedInstance, someVariableKey))):
                #print('found bound method (not adding this) ', someVariableKey, ': ', getattr(passedInstance, someVariableKey))
                classInstanceDict[someVariableKey] = "event"
            elif(isclass(type(getattr(passedInstance, someVariableKey))) and not type(getattr(passedInstance, someVariableKey)).__name__ in dataTypesPython):
                #For now just set the value to be the name of the class, will build functionality to put in list of identifiers as a string. Ex: 'ClassName(id0:val0, id1:val1)'
                #print('found custom class or type ', someVariableKey, ': ', getattr(passedInstance, someVariableKey))
                classInstanceDict[someVariableKey] = "className(id0:val0, id1:val1, ...)"
            #Other cases are cleared, so it is either good or it is unaccounted for so we should let it throw an error.
            else:
                #print('Standard type: ', type(getattr(passedInstance, someVariableKey)), getattr(passedInstance, someVariableKey))
                classInstanceDict[someVariableKey] = getattr(passedInstance, someVariableKey)
        return classInstanceDict


    #Converts a passed in list or tuple into a json dictionary where the keys are the datatypes in python
    def convertTupleOrListToJSONdict(self, passedSet):
        returnVal = {"__" + type(passedSet).__name__ + "__0":{}}
        someDict = returnVal["__" + type(passedSet).__name__ + "__0"]
        for elem in passedSet:
            #Handles Cases where particular classes must be converted into a string format.
            if(type(elem).__name__ == 'dateTime'):
                someDict[self.getJsonTypeKeyNumber(typeName='dateTime', someDict=someDict)] = "someDateTime"
            elif(type(elem).__name__ == 'TextIOWrapper'):
                someDict[self.getJsonTypeKeyNumber(typeName='TextIOWrapper', someDict=someDict)] = "OpenedFile"
            elif(type(elem).__name__ == 'bytes' or type(elem).__name__ == 'bytearray'):
                #print('found byte var ', someVariableKey, ': ', classInstanceDict[someVariableKey])
                someDict[self.getJsonTypeKeyNumber(typeName=type(elem).__name__, someDict=someDict)] = elem.decode()
            elif(type(elem).__name__ == 'tuple' or type(elem).__name__ == 'list'):
                print('adding a tuple or list: ', elem)
                someDict[self.getJsonTypeKeyNumber(typeName=type(elem).__name__, someDict=someDict)] = self.convertTupleOrListToJSONList(passedSet=elem)
            elif(type(elem).__name__ == 'dict'):
                print('trying to add a dict', elem)
            elif(ismethod(elem)):
                #print('found bound method (not adding this) ', someVariableKey, ': ', getattr(passedInstance, someVariableKey))
                someDict[self.getJsonTypeKeyNumber(typeName="event", someDict=someDict)] = "event"
            elif(isclass(type(elem)) and not type(elem).__name__ in dataTypesPython):
                #For now just set the value to be the name of the class, will build functionality to put in list of identifiers as a string. Ex: 'ClassName(id0:val0, id1:val1)'
                #print('found custom class or type ', someVariableKey, ': ', getattr(passedInstance, someVariableKey))
                someDict[self.getJsonTypeKeyNumber(typeName=type(elem).__name__, someDict=someDict)] = "className(id0:val0, id1:val1, ...)"
            #Other cases are cleared, so it is either good or it is unaccounted for so we should let it throw an error.
            else:
                #print('Standard type: ', type(getattr(passedInstance, someVariableKey)))
                someDict[self.getJsonTypeKeyNumber(typeName=type(elem).__name__, someDict=someDict)] = elem
            return returnVal

    def getJsonTypeKeyNumber(self, typeName, someDict):
        topTypeNum = 0
        for someKey in someDict.keys():
            if(type(someKey) == 'str'):
                if(someKey.__contains__("__" + typeName + "__")):
                    curTypeNum = int(someKey[someKey.index("__" + typeName + "__") + len(typeName) + 4:])
                    if(curTypeNum > topTypeNum):
                        topTypeNum = curTypeNum
        return "__" + typeName + "__" + str(topTypeNum + 1)
        