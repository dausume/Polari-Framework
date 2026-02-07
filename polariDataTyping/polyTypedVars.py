from polariApiServer.remoteEvents import *
from objectTreeDecorators import *
from polariDataTyping.dataTypes import pythonTypeToSqliteAffinity
import logging


class polyTypedVariable(treeObject):
    @treeObjectInit
    def __init__(self, polyTypedObj=None, attributeName=None, attributeValue=None):
        #The name of the variable in the class
        self.polyTypedObj = polyTypedObj
        self.name = attributeName
        self.analyzeValuesMode = True
        self.manager = polyTypedObj.manager
        #if(polyTypedObj == 'testObj'):
        #    print('Making testObj on polariServer for variable: ', attributeName)
        #Breaks down a data type into the programming language name of the data type,
        #the datatype defined for it, and the number of symbols (regardless of type)
        #that must be used in order to define it.
        dataType = type(attributeValue).__name__
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
                if(elemType == 'list' or elemType == 'tuple' or elemType == 'dict' or elemType == 'polariList'):
                    tempString = self.extractSetTyping(varSet=elem,typingString=typingString, curDepth = curDepth + 1, maxDepth=maxDepth)
                else:
                    tempString = elemType
                if(not tempString in typingString):
                    tempString += ','
                    typingString += tempString
        elif(setType == 'dict'):
            for elem in varSet.keys():
                elemType = type(elem).__name__
                if(elemType == 'list' or elemType == 'tuple' or elemType == 'dict' or elemType == 'polariList'):
                    tempString = self.extractSetTyping(varSet=elem,typingString=typingString, curDepth = curDepth + 1, maxDepth=maxDepth)
                else:
                    tempString = elemType
                tempString += ':'
                elemType = type(varSet[elem]).__name__
                if(elemType == 'list' or elemType == 'tuple' or elemType == 'dict' or elemType == 'polariList'):
                    tempString += self.extractSetTyping(varSet=varSet[elem],typingString=typingString, curDepth = curDepth + 1, maxDepth=maxDepth)
                else:
                    tempString += elemType
                if(not tempString in typingString):
                    tempString += ','
                    typingString += tempString
        # Remove trailing comma only if elements were added
        if(typingString.endswith(',')):
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
        return (sourceTypeDict, sinkTypeDict)
    def analyzeVarValue(self, variableValue):
        dataTypesPython = ['str','int','float','complex','list','tuple','range','dict','set','frozenset','bool','bytes','bytearray','memoryview', 'NoneType']
        newValueTypingEntry = "NoneType"
        curAttrType = type(variableValue).__name__
        valueHolder = None
        # Verbose logging - commented out for cleaner output
        # print("adding elem of type ", curAttrType ," with value: ", variableValue)
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
        elif(curAttrType == 'dict' or curAttrType == 'tuple' or curAttrType == 'list' or curAttrType == 'polariList'):
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

    def updateTypingDicts(self, typingResult):
        """Update typingDicts with a new analysis result from analyzeVarValue().

        If the type already exists in typingDicts, increments its occurrence count.
        If it's a new type, appends a new entry.

        Args:
            typingResult: Dict returned by analyzeVarValue(), e.g. {"type": "str", "length": 5}
                         or a string like "NoneType" for edge cases.

        Returns:
            Deviation classification string: 'match', 'widenable', 'variant', or 'complex'
        """
        if typingResult is None:
            return 'match'
        # Normalize typingResult to get type string
        if isinstance(typingResult, dict):
            newType = typingResult.get('type', 'NoneType')
        elif isinstance(typingResult, str):
            newType = typingResult
        else:
            return 'match'

        # Check if this type already exists in typingDicts
        for entry in self.typingDicts:
            if entry['dataType'] == newType:
                entry['occurences'] += 1
                return 'match'

        # New type encountered - classify the deviation before adding
        deviation = self.classifyDeviation(newType)

        # Add new typingDicts entry
        symbolCount = typingResult.get('length', 0) if isinstance(typingResult, dict) else 0
        self.typingDicts.append({
            "language": 'python',
            "manager": self.typingDicts[0]["manager"] if self.typingDicts else tuple(),
            "dataType": newType,
            "symbolCount": symbolCount,
            "occurences": 1
        })

        return deviation

    def _getSqliteAffinity(self, pythonTypeName):
        """Get the SQLite affinity for a Python type name.

        Args:
            pythonTypeName: String name of the Python type

        Returns:
            SQLite affinity string
        """
        return pythonTypeToSqliteAffinity(pythonTypeName)

    def classifyDeviation(self, newType):
        """Classify how a new type deviates from existing types.

        Implements three-way decision logic:
        - 'widenable': same SQLite affinity family (e.g., int with more digits, or int→float).
                       Just modify the current table column slightly.
        - 'variant': different affinity family (e.g., int→dict).
                     Fundamentally different → needs an alternate/variant table.
        - 'complex': 3+ distinct affinity families already present.
                     Too many variants → store tree-branch IDs in tuple format.

        Args:
            newType: String name of the new Python type

        Returns:
            Classification string: 'match', 'widenable', 'variant', or 'complex'
        """
        newAffinity = self._getSqliteAffinity(newType)

        # Collect all existing distinct affinities
        existingAffinities = set()
        for entry in self.typingDicts:
            existingAffinities.add(self._getSqliteAffinity(entry['dataType']))

        # If the new affinity is already represented, it's widenable at worst
        if newAffinity in existingAffinities:
            return 'widenable'

        # Adding a new affinity - check how many we'd have
        totalAffinities = len(existingAffinities | {newAffinity})

        if totalAffinities >= 3:
            return 'complex'
        else:
            return 'variant'

    def getDeviationSummary(self):
        """Get a summary of the variable's current deviation status.

        Returns:
            Dict with keys:
                - dominantType: most common Python type name
                - dominantAffinity: SQLite affinity of the dominant type
                - distinctTypeCount: number of distinct Python types seen
                - distinctAffinityCount: number of distinct SQLite affinities
                - totalOccurrences: total occurrence count across all types
                - schemaStrategy: 'typed', 'widenable', 'variant', or 'complex'
                - sqliteAffinity: the recommended SQLite affinity for column creation
        """
        if not self.typingDicts:
            return {
                'dominantType': 'NoneType',
                'dominantAffinity': 'NONE',
                'distinctTypeCount': 0,
                'distinctAffinityCount': 0,
                'totalOccurrences': 0,
                'schemaStrategy': 'typed',
                'sqliteAffinity': 'NONE'
            }

        # Find dominant type (most occurrences)
        dominantEntry = max(self.typingDicts, key=lambda e: e['occurences'])
        dominantType = dominantEntry['dataType']
        dominantAffinity = self._getSqliteAffinity(dominantType)

        # Count distinct types and affinities
        distinctTypes = set(e['dataType'] for e in self.typingDicts)
        distinctAffinities = set(self._getSqliteAffinity(e['dataType']) for e in self.typingDicts)
        totalOccurrences = sum(e['occurences'] for e in self.typingDicts)

        # Determine schema strategy
        if len(distinctAffinities) == 1:
            strategy = 'typed' if len(distinctTypes) == 1 else 'widenable'
        elif len(distinctAffinities) == 2:
            strategy = 'variant'
        else:
            strategy = 'complex'

        return {
            'dominantType': dominantType,
            'dominantAffinity': dominantAffinity,
            'distinctTypeCount': len(distinctTypes),
            'distinctAffinityCount': len(distinctAffinities),
            'totalOccurrences': totalOccurrences,
            'schemaStrategy': strategy,
            'sqliteAffinity': dominantAffinity
        }

    #MAKES A conversionTest Remote Event, which causes the data to be returned in
    #a response after it has been converted and before it has any operations performed
    #on it.
    #Detects a variable with a particular value to another language using default
    #conversions, then recieves that same value after it has been returned to python
    #both are analyzed as converted strings to assess if they are still the same value.
    #def isLosslessConversion(self, attributeTypingDict):
    #    define something here!!