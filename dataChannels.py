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
from managedFiles import *
import os, json, logging, datetime

#A file used to manage JSON for a particular Polari or App.
class dataChannel(managedFile):
    def __init__(self, name=None):
        managedFile.__init__(self, name=name, extension='json')
        #The JSON currently being manipulated in the python object
        self.jsonDict = []
        #The recorded JSON from the last time the JSON File was read.
        self.lastFileReadJSON = []
        #The current system performing operations on the file, according to last reading.
        #Ex: (sourceClass:Polari, sourceName:polariName)
        self.currentOwner = (None, None)
        #Register for the different Sources which may contribute data to this JSON File, and their access order.
        self.sourceRegister = []
        #Register for the different Sinks which consume data from this JSON File, and their access order.
        self.sinkRegister = []
        #The date-time when the last source claimed ownership of the JSON File.
        self.lastOccupationDateTime = None
        #The date-time when the most current source claimed ownership of the JSON File.
        self.occupationDateTime = None

    #The function called by an App or Polari when it looks through the dataChannel for requests
    #intended for itself.
    def channelIteration(self):
        available = self.checkChannelAvailability()
        

    #Injects all JSON currently in the jsonDict variable, into the JSON file.
    def injectJSON(self):
        if(self.checkChannelAvailability()):
            (self.jsonDict).pullDataComms()
            self.openFile()
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
        self.lastFileReadJSON = json.load(self.fileInstance)
        self.closeFile()
        accessDataSets = self.getClassDataSets('dataChannel')
        setIndex = 0
        occupationIndex = None
        lastOccupationDateTime = None
        for dataSet in accessDataSets:
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
    def occupyChannel(self):
        #open the file
        self.openFile()
        #If we successfully open the file, pull information from there.
        if(self.checkChannelAvailability()):
            #If file is opened, and we detect that the file does not have another Owner acting on it currently, and we claim it.
            self.currentOwner = ((self.manager).__class__, (self.manager).name)
            self.occupationDateTime = datetime.datetime.now()
            json.dump(
                getJSONdictForClass(definingFile='managedDataComms', className='dataChannel', passedInstances=self),
                self.fileInstance
            )

    def openChannel(self):
        #open the file
        self.openFile()
        #If we successfully open the file, and make sure it is owned by this dataChannel object.
        if(self.checkChannelAvailability()):
            #If file is opened, and we detect that the file does not have another Owner acting on it currently, and we claim it.
            self.currentOwner = (None, None)
            json.dump(
                getJSONdictForClass(definingFile='managedDataComms', className='dataChannel', passedInstances=self),
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
                duplicationDataSetTuple = hasDuplicateDataSet(newDataSet)
                if(duplicationDataSetTuple[0]): #A duplicate data set was found.
                    #Iterates through each instance in the dataSet which was found to be the duplicate of the new dataSet
                    instanceIndex = 0
                    duplicateTuples = matchDuplicateInstances()
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
        if(self.jsonDict != None):
            for dataSet in (self.jsonDict):
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
def getJSONdictForClass(absDirPath = os.path.dirname(os.path.realpath(__file__)),
                    definingFile = os.path.realpath(__file__)[os.path.realpath(__file__).rfind('\\') + 1 : os.path.realpath(__file__).rfind('.')],
                    className = 'testClass', passedInstances = None):
    #If an instance or list of instances of the same type are passed, grabs the class name.
    if(passedInstances!=None):
        if(isinstance(passedInstances, list)):
            className = passedInstances[0].__class__.__name__
        else:
            className = passedInstances.__class__.__name__
    #Gives access to the class by importing it and simultaneously passes in the method for instantiating it.
    returnedClassInstantiationMethod = getAccessToClass(absDirPath, definingFile, className, True)
    classVarDict = [
        {
            "class":className,
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
            print('Printing Class Info: ' + str(classInfoDict))
            for classElement in classInfoDict:
                if(not callable(classElement)):
                    classInstanceDict[classElement] = None
            classVarDict[0]["data"].append( getJSONclassInstance(someInstance, classInstanceDict) )
    elif(passedInstances == None):
        if(passedInstances == None):
            classInstance = returnedClassInstantiationMethod()
            classInfoDict = classInstance.__dict__
    else: #Accounts for the case where only a single instance of the class is passed into the function
        classInstanceDict = {}
        classInfoDict = passedInstances.__dict__
        for classElement in classInfoDict:
            #print('got attribute: ' + classElement)
            if(not callable(classElement)):
                classInstanceDict[classElement] = None
                #print('not callable attribute: ' + classElement)
        classVarDict[0]["data"].append( getJSONclassInstance(passedInstances, classInstanceDict) )
    return classVarDict

#Takes in all information needed to access a class and returns a formatted json string 
def getJSONforClass(absDirPath = os.path.dirname(os.path.realpath(__file__)),
                    definingFile = os.path.realpath(__file__)[os.path.realpath(__file__).rfind('\\') + 1 : os.path.realpath(__file__).rfind('.')],
                    className = 'testClass', passedInstances = None):
    classVarDict = getJSONdictForClass(absDirPath=absDirPath,definingFile=definingFile,className=className, passedInstances=passedInstances)
    JSONstring = json.dumps(classVarDict)
    return JSONstring

def getJSONclassInstance(passedInstance, classInstanceDict):
    for someVariableKey in classInstanceDict.keys():
        classInstanceDict[someVariableKey] = getattr(passedInstance, someVariableKey)
        #Handles Cases where particular classes must be converted into a string format.
        if(type(classInstanceDict[someVariableKey]).__name__ == 'dateTime'):
            classInstanceDict[someVariableKey] = 'someDateTime'
        elif(type(classInstanceDict[someVariableKey]).__name__ == 'TextIOWrapper'):
            classInstanceDict[someVariableKey] = 'OpenedFile'
    return classInstanceDict