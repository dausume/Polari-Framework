from polariApiServer.remoteEvents import *
from objectTreeDecorators import *
import logging


class polyTypedVariable(treeObject):
    @treeObjectInit
    def __init__(self, polyTypedObj=None, attributeName=None, attributeValue=None):
        #The name of the variable in the class
        print("starting ptv init")
        self.polyTypedObj = polyTypedObj
        self.name = attributeName
        self.analyzeValuesMode = True
        print("setting manager")
        self.manager = polyTypedObj.manager
        #if(polyTypedObj == 'testObj'):
        #    print('Making testObj on polariServer for variable: ', attributeName)
        #Breaks down a data type into the programming language name of the data type,
        #the datatype defined for it, and the number of symbols (regardless of type)
        #that must be used in order to define it.
        dataType = type(attributeValue).__name__
        print("analyze value in init")
        self.typingVariationDict = self.analyzeVarValue(attributeValue)
        self.eventsList = []
        #Accounts for different set-like data types and what may be contained inside.
        if(callable(attributeValue)):
            self.eventsList.append(attributeValue)
        if(dataType == 'list' or dataType == 'tuple' or dataType == 'dict' or dataType == 'polariList'):
            dataType = self.extractSetTyping(varSet=attributeValue)
        elif(not dataType in dataTypesPython and dataType != 'NoneType' and dataType != 'method'):
            #Find the definition of the object for the given manager, and construct based on that.
            #Case where the object is not accounted for by the manager with a PolyTyping Instance.
            #print('Getting object of type, ', dataType, 'as an object.')
            obj = self.polyTypedObj.manager.getObjectTyping(classInstance=attributeValue)
            if(None == obj):
                obj = self.polyTypedObj.manager.makeDefaultObjectTyping(classInstance=attributeValue)
            #If the variable being set is a manager, make certain it is a manager object.
            if(self.name == "manager"):
                if(obj.checkIfManagerObject()):
                    #Confirms the object being set is a manager object.
                    obj.addToObjReferenceDict(referencedClassObj=attributeValue.__class__, referenceVarName=self.name)
                    #print("ADDING to REFERENCE DICTIONARY FROM polyTypedVar initialization on object ", self.polyTypedObj, " for variable ", self.name)
                else:
                    varType = attributeValue.__class__.__name__
                    errMsg = "Found attempt to set non-manager object value of type "+varType+" on manager."
                    print(errMsg)
            else:
                if(obj.checkIfManagerObject() or obj.checkIfTreeObject()):
                    #Confirms
                    obj.addToObjReferenceDict(referencedClassObj=attributeValue.__class__, referenceVarName=self.name)
                    #print("ADDING to REFERENCE DICTIONARY FROM polyTypedVar initialization on object ", self.polyTypedObj, " for variable ", self.name)
                    if(obj.checkIfManagerObject()):
                        #TODO Make functionality to connect a subordinate tree here.
                        pass
                else:
                    print("Found attempt to set non-treeObject object or unaccounted for value onto variable.")
            #self.polyTypedObj.addToObjReferenceDict(referencedClassObj=attributeValue.__class__, referenceVarName=self.name)
            #print("ADDING to REFERENCE DICTIONARY FROM polyTypedVar initialization on object ", self.polyTypedObj, " for variable ", self.name)
            #TEMPORARY SOLUTION: Just put anything I can't find as an object.
            dataType = 'object(' + dataType + ')'
        symbolCount = len(str(attributeValue))
        #Each typing dictionary contains the programming language, context (Object, ObjIdentifiers)
        #
        self.typingDicts = [{"language":'python',"manager":tuple([type(polyTypedObj.manager).__name__, (polyTypedObj.manager)]),"dataType":dataType,"symbolCount":symbolCount,"occurences":1}]
        self.pythonTypeDefault = dataType

    #Pulls apart a set-typed variable (dict, list, or tuple)
    def extractSetTyping(self, varSet, typingString = '', curDepth=1, maxDepth=3):
        setType = type(varSet).__name__
        typingString = setType + '('
        if(curDepth >= maxDepth):
            return setType + '(?)'
        firstRun = True
        if(setType == 'list' or setType == 'tuple' or setType == 'polariList'):
            for elem in varSet:
                elemType = type(elem).__name__
                if(elemType == 'list' or elemType == 'tuple' or elemType == 'dict' or setType == 'polariList'):
                    tempString = self.extractSetTyping(varSet=elem,typingString=typingString, curDepth = curDepth + 1, maxDepth=maxDepth)
                else:
                    tempString = elemType
                if(not tempString in typingString):
                    tempString += ','
                    typingString += tempString
        elif(setType == 'dict'):
            for elem in varSet.keys():
                elemType = type(elem).__name__
                if(elemType == 'list' or elemType == 'tuple' or elemType == 'dict' or setType == 'polariList'):
                    tempString = self.extractSetTyping(varSet=elem,typingString=typingString, curDepth = curDepth + 1, maxDepth=maxDepth)
                else:
                    tempString = elemType
                tempString += ':'
                elemType = type(varSet[elem]).__name__
                if(elemType == 'list' or elemType == 'tuple' or elemType == 'dict' or setType == 'polariList'):
                    tempString += self.extractSetTyping(varSet=elem,typingString=typingString, curDepth = curDepth + 1, maxDepth=maxDepth)
                else:
                    tempString += elemType
                if(not tempString in typingString):
                    tempString += ','
                    typingString += tempString
        typingString = typingString[:-1]
        typingString += ')'
        return typingString

    #Where the object passed in is the value or values of the list of this polyTypedVariable,
    #we retrieve the key - self.polyTypedObject, from the objectReferencesDict of the passed in obj,
    #and ensure that our current variable's name is within the list which is the value owned by that key.
    #def addToObjReferenceDict(self, classObj):
    #    if(hasattr(self, 'polyTypedObj')):
    #        print('Adding obj ', classObj, ' to object ref dict of ', self.polyTypedObj.className, ' for variable named: ', self.name)
    #        for objType in self.polyTypedObj.manager.objectTyping:
    #            if(objType.className == classObj.__name__):
    #                if(not self.polyTypedObj.className in objType.objectReferencesDict):
    #                    objType.objectReferencesDict[self.polyTypedObj.className] = [self.name]
    #                elif(not self.name in objType.objectReferencesDict[self.polyTypedObj.className]):
    #                    (objType.objectReferencesDict[self.polyTypedObj.className]).append(self.name)
    #     else:
    #        print('Attempting to set object reference for object ')

    #Allows you to get what the expected variable types should be for a variable
    #as well as what type they should be converted to when they arrive at their
    #destination.
    def getConversionValues(self, sourceLanguage, sinkLanguage):
        #Makes a list of key-value pairs for each variable and it's expectation
        #data types (the potential data types used in that language, and their
        #default conversion type, which is the type most used or most encompassing)
        sourceLanguageVarTypes = []
        sinkLanguageVarTypes = []
        #Adds all variable variations into the lists for their language
        #Both are if statements (in order to account for conversions where both
        #source and sink are the same language in a different context)
        for varDict in self.typingDicts:
            if(varDict['language'] == sourceLanguage):
                sourceLanguageVarTypes.append(varDict)
            if(varDict['language'] == sinkLanguage):
                sinkLanguageVarTypes.append(varDict)
        sourceTypeDict = None
        greatestOccNum = 0
        for varDict in sourceLanguageVarTypes:
            if(varDict['occurences'] > greatestOccNum):
                greatestOccNum = varDict['occurences']
                sourceTypeDict = varDict
        sinkTypeDict = None
        greatestOccNum = 0
        for varDict in sinkLanguageVarTypes:
            if(varDict['occurences'] > greatestOccNum):
                greatestOccNum = varDict['occurences']
                sinkTypeDict = varDict
        
    def analyzeVarValue(self, variableValue):
        dataTypesPython = ['str','int','float','complex','list','tuple','range','dict','set','frozenset','bool','bytes','bytearray','memoryview', 'NoneType']
        newValueTypingEntry = "NoneType"
        curAttrType = type(variableValue).__name__
        valueHolder = None
        #print("adding elem of type ", curAttrType ," with value: ", curAttr)
        #Handles Cases where particular classes must be converted into a string format.
        if(curAttrType == 'dateTime'):
            #All date-time values occupy the same amount of space in db.
            newValueTypingEntry = {"type":"dateTime"}
        elif(curAttrType == 'TextIOWrapper'):
            #Information about data can be extracted from polariFile objects.
            newValueTypingEntry = {"type":"TextIOWrapper"}
        elif(curAttrType == 'bytes'):
            #Get the number of bytes for more detailed typing.
            valueHolder = variableValue.decode()
            newValueTypingEntry = {"type":"bytes"}
        elif(curAttrType == 'bytearray'):
            #Get the number of bytes for more detailed typing.
            valueHolder = variableValue.decode()
            newValueTypingEntry = {"type":"bytearray"}
        elif(curAttrType == 'dict'):
            classInstanceDict[self.name] = self.convertSetTypeIntoJSONdict(variableValue)
        elif(curAttrType == 'tuple' or curAttrType == 'list' or curAttrType == 'polariList'):
            newValueTypingEntry = {"type":self.extractSetTyping(varSet=variableValue)}
        elif(inspect.ismethod(variableValue)):
            newValueTypingEntry = {"type":"classmethod(" + variableValue.__name__ + ")"}
        elif(inspect.isclass(type(variableValue)) and not curAttrType in dataTypesPython):
            newValueTypingEntry = {"type":"classreference(" + variableValue.__class__.__name__ + ")"}
        #Other cases are cleared, so it is either good or it is unaccounted for so we should let it throw an error.
        elif(curAttrType in dataTypesPython):
            newValueTypingEntry = {"type":curAttrType}
            if(curAttrType == "int" or curAttrType == "dbl"):
                newValueTypingEntry["length"] = len(str(variableValue))
            if(curAttrType == "str"):
                newValueTypingEntry["length"] = len(curAttrType)
        else:
            newValueTypingEntry = "unaccountedType(" + variableValue.__name__ + ")"
        return newValueTypingEntry

    #MAKES A conversionTest Remote Event, which causes the data to be returned in
    #a response after it has been converted and before it has any operations performed
    #on it.
    #Detects a variable with a particular value to another language using default
    #conversions, then recieves that same value after it has been returned to python
    #both are analyzed as converted strings to assess if they are still the same value.
    #def isLosslessConversion(self, attributeTypingDict):
    #    define something here!!