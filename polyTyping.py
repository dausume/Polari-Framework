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
#from definePolari import *
#from managedApp import *
from remoteEvents import *
from objectTreeDecorators import *
#from functionalityAnalysis import *

import logging

#Accounts for data on a class and allows for valid data typing in multiple types,
#also accounts for the conversion of data types that should be performed when
#transmitting data across environments and into other programming language contexts.
class polyTypedObject(treeObject):
    @treeObjectInit
    def __init__(self, className, manager, objectReferencesDict={}, sourceFiles=[], identifierVariables=[], variableNameList=[]):
        if(className == 'polariServer'):
            print('Making the polyTyping object for polariServer with manager set as: ', manager)
        self.isTreeObject = None
        self.isManagerObject = None
        self.className = className
        #The list of objects that have variables which reference this object, either as a single
        #instance, or as a list of the instances.
        self.objectReferencesDict = objectReferencesDict
        #A list of managed files that defined this class for different languages.
        #print('passed source files: ', sourceFiles)
        self.sourceFiles = sourceFiles
        #The context (App or Polari) in which this Object is being utilized
        self.manager = manager
        #The instances of this object's polyTyping in higher tiered contexts.
        self.inheritedTyping = []
        #Variables that may be used as unique identifiers.
        if(identifierVariables == [] or identifierVariables == ['id']):
            self.identifiers = ['id']
        elif(type(identifierVariables).__name__ == 'list'):
            self.identifiers = identifierVariables
        else:
            #This should probably throw an error, but I'll just be nice and autocorrect it to the default if someone messes things up for now.
            self.identifiers = ['id']
        #The names of all of the Variables for the class.
        self.variableNameList = variableNameList
        #The polyTypedVariable instances for each of the variables in the class.
        self.polyTypedVars = []

    #Where the object passed in is the value or values of the list of this polyTypedVariable,
    #we retrieve the key - self.polyTypedObject, from the objectReferencesDict of the passed in obj,
    #and ensure that our current variable's name is within the list which is the value owned by that key.
    def addToObjReferenceDict(self, referencedClassObj, referenceVarName):
        if(hasattr(self, 'manager')):
            #print('Adding obj ', classObj, ' to object ref dict of ', self.className, ' for variable named: ', varName)
            for objType in self.manager.objectTyping:
                if(objType.className == referencedClassObj.__name__):
                    if(not self.className in objType.objectReferencesDict):
                        self.objectReferencesDict[self.className] = [referenceVarName]
                    elif(not self.name in objType.objectReferencesDict[self.polyTypedObj.className]):
                        (objType.objectReferencesDict[self.className]).append(referenceVarName)
                break
        else:
            print('Attempting to set object reference on object that is not fully defined.')

    def treeOrManager(self):
        for srcFile in objType.sourceFiles:
            if(srcFile.extension == 'py'):
                accessFile = srcFile
                break
        moduleImported = __import__(name=accessFile.name, fromlist=self.className)
        for name, obj in inspect.getmembers(moduleImported):
            if(name == self.className):
                from objectTreeDecorators import treeObject
                from objectTreeManagerDecorators import managerObject
                if( issubclass(obj, treeObject) ):
                    self.isTreeObject = True
                    self.isManagerObject = False
                if( issubclass(obj, managerObject) ):
                    self.isTreeObject = False
                    self.isManagerObject = True
                

    #Creates typing for the instance by analyzing it's variables and creating
    #default polyTypedVariables for it.
    def analyzeInstance(self, pythonClassInstance):
        classInfoDict = pythonClassInstance.__dict__
        for someVariableKey in classInfoDict:
            if(not callable(classInfoDict[someVariableKey])):
                #print('accVar: ' + someVariableKey)
                var = getattr(pythonClassInstance, someVariableKey)
                #If the var is accounted for, analyze the current value.
                self.analyzeVariableValue(pythonClassInstance=pythonClassInstance, varName=someVariableKey, varVal=var)
        #print('Showing all polytyped Var for object ' + self.className + ': ', self.polyTypedVars)


    def analyzeVariableValue(self, pythonClassInstance, varName, varVal):
        #print('Analyzing variable ' + varName + ' in class ' + self.className)
        numAccVars = len(self.polyTypedVars)
        foundVar = False
        for polyVar in self.polyTypedVars:
            #If the variable is found, account for it on it's typeDicts.
            if(polyVar.name == varName):
                foundVar = True
                break
        if not foundVar:
            #print('Adding new polyTypedVar ' + varName)
            newPolyTypedVar = polyTypedVariable(polyTypedObj=self, attributeName=varName, attributeValue=varVal, manager=self.manager)
            (self.polyTypedVars).append(newPolyTypedVar)

    #Uses the Identifiers and the class name
    def makeTypedTable(self):
        pySource = None
        for sourceFile in self.sourceFiles:
            if((sourceFile.extension) == 'py'):
                 pySource = sourceFile
        ((self.manager).DB).makeTableByClass(absDirPath=sourceFile.Path, definingFile=sourceFile.name)

    def getObjectTyping(self, classObj=None, className=None, classInstance=None ):
        if className != None:
            for objType in (self.manager).objectTyping:
                if(objType.className == className):
                    return objType
        elif classInstance != None:
            for objType in (self.manager).objectTyping:
                if(objType.className == classInstance.__class__.__name__):
                    return objType
        elif classObj != None:
            for objType in (self.manager).objectTyping:
                if(objType.className == classObj.__name__):
                    return objType
        else:
            print("You called the \'getObjectTyping\' function without passing any parameters!  Must pass one of the three parameter options, the string name of the class, an instance of the class, or the class defining object itself \'__class__\'.")
        obj = None
        if className != None:
            print("Attempted to retrieve a polyTypedObject that does not exist \"", className, "\" using it\'s name as a string.  Cannot generate a default polyTypedObject using a passed string, pass either an object instance or the class object \'__class__\' to generate a default polyTypedObject.")
        elif classInstance != None:
            obj = (self.manager).makeDefaultObjectTyping(classInstance=classInstance)
        elif classObj != None:
            obj = (self.manager).makeDefaultObjectTyping(classObj=classObj)
        return obj

    def getInstanceIdentifiers(self, instance):
        obj = self.getObjectTyping(type(instance).__name__)
        idVars = obj.identifiers
        #Compiles a dictionary of key-value pairs for the identifiers 
        identifiersDict = {}
        for id in idVars:
            identifiersDict[id] = getattr(instance,id)
        return identifiersDict

    def getActiveInstances(self):
        #Retrieves the generalized dictionary which describes a tree showing how the manager
        #instance (an app or polari, generally) is related to the given object being described
        #by this polyTypedObject instance.
        keys = (self.objectReferencesDict).keys()
        #A dictionary of the active instances of this object that sit directly on variables of
        #the manager object.
        instancesList = []
        managerInstanceVarsList = None
        #Checks if the manager has instances sitting on it directly.
        if(type(self.manager).__name__ in keys):
            #Gets the list of variable names that directly reference this objecct or lists of it.
            managerInstanceVarsList = (self.objectReferencesDict)[type(self.manager).__name__]
            #Goes through the variables on the manager object and pulls the instances from them.
            for num in managerInstanceVarsList:
                value = getattr( self.manager, managerInstanceVarsList[num] )
                if(type(value) == list):
                    for inst in value:
                        instancesList.append(inst)
                else:
                    instancesList.append(value)
        baseTuple = (type(self.manager).__name__, self.getInstanceIdentifiers(self.manager), self.manager)
        #A dictionary/tree which shows all objects with their identifiers which reference this object.
        objectTree = {baseTuple:{}}
        #An ordered list of tuples (or a stack) which shows the current traversal of objects.
        objectTraversalPath = [baseTuple]
        #A list of objects that have variables which could potentially hold more instances.
        #Go though every potential object and see if it has potential references on the manager.
        potentialObjects = []
        #A list of all object instances referenced on the current object, regardless of relation.
        traversalObjects = []
        mngObj = self.getObjectTyping( type(self.manager).__name__ )
        #Checks each Object see if the current object (the manager) has any potential references to it.
        #Generates a list of potentialObjects, which may potentially hold instances of the desired obj.
        for obj in (self.manager).objectTyping:
            #Gets the list of all objects referenced in variables on the given object definition.
            referenceVarsList = (obj.objectReferencesDict)[type(self.manager).__name__]
            #Checks if the manager object has this object and the desired object referenced.
            if type(self.manager).__name__ in (obj.objectReferencesDict).keys() and self.className in (obj.objectReferencesDict).keys():
                for var in referenceVarsList:
                    value = getattr(self.manager, var)
                    if(type(value) == list):
                        for inst in value:
                            potentialObjects.append(inst)
                            traversalObjects.append(inst)
                    else:
                        potentialObjects.append(value)
                        traversalObjects.append(value)
            #Checks if the manager object has this object referenced anywhere on it at all.
            elif type(self.manager).__name__ in (obj.objectReferencesDict).keys():
                for var in referenceVarsList:
                    value = getattr(self.manager, var)
                    if(type(value) == list):
                        for inst in value:
                            traversalObjects.append(inst)
                    else:
                        traversalObjects.append(value)
            #Go through each potential object and check to ensure it is not already accounted
            #for inside the objectTree, if it is not, then add it to the tree.
            for obj in traversalObjects:
                objTuple = (type(obj).__name__,
                                    self.getInstanceIdentifiers(obj),
                                    obj)
                if(isTupleInTree(tree=objectTree,traversalList=baseTuple,instanceTuple=objTuple)):
                    getTreeBranch()
        #First, get all objects which have references to this object on them.
        #Then, get all references to those objects on a given instance of the manager object.
        #Retrieve those instances and use tuples to track them (className,identifiersList,instance,traversed)
        #Compile a list of those tuples, then check the already existing tree and remove any with
        #matching classNames & identifiersLists, then use the objectTraversalPath to access the
        #appropriate node (at this time an empty dictionary) in the tree and put all valid
        #tuples into that dictionary as new tuple-dictionary pairs.
        #self.objectTraversal()
        return objectTree

    #Will go through every dictionary in the tree and return True if the tuple exists anywhere.
    def isTupleInTree(self, tree, traversalList, instanceTuple):
        found = False
        branch = self.getTreeBranch(tree = tree, traversalList = traversalList)
        for branchTuple in branch.keys():
            if branchTuple[0] == instanceTuple[0] and branchTuple[0] == instanceTuple[0]:
                return True
        for branchTuple in branch.keys():
            found = self.isTupleInTree(tree=tree,traversalList=traversalList+[branchTuple],instanceTuple=instanceTuple)
            if(found):
                return True
        return found
    
    def getTreeBranch(self, tree, traversalList):
        branch = tree
        for tup in traversalList:
            branch = tree[tup]
        return branch
            
    #Allows the traversal of objects using known paths to retrieve object instances of the
    #given type.
    #Uses a combination of the original dictionary (self.activeObjectsDict) in addition to the
    #traversalDictionary to get the instances of the object from all related objects.
    def objectTraversal(self, sourceInstance, originalActiveObjectsDict, traversalDictionary):
        #the variables specified as being specified as instances or lists of instances of the
        #desired object.
        traversalKeys = traversalDictionary.keys()
        baseList = []
        for key in traversalKeys:
            #Gets all of the keys for instances and lists of instances immediately located
            #on this instance.
            if( type(key) == int ):
                baseList.append(key)
        originKeys = originalActiveObjectsDict.keys()
        

    def makeGeneralizedTable(self):
        managerDB = (self.manager).DB
        definingFile = None
        for sourceFile in sourceFiles:
            if sourceFile.contains('.py'):
                definingFile=sourceFile
        #managerDB.makeTableByClass(absDirPath, definingFile=, className)

    #First, pull in all of the instances from the json dictionary,
    #and for each instance load them on first as they are pulled from the
    #key-value pairings.  Second, go through each of the newly generated
    #Object Instances, and convert them according to 
    def convertJSONvarsToObjectInstances(self, jsonDict):
        for instance in jsonDict:
            break

    def addObjTypingToManager(self):
        foundExisting = False
        for typedObj in ((self.manager).objectTyping):
            if(typedObj.className == self.className):
                foundExisting = True
        if not foundExisting:
            ((self.manager).objectTyping).append(self)
        else:
            logging.warn(msg='Attempting to generate Object typing that already exists '
            + 'for ' + self.className + 'in the context of a ' + (self.manager).__name__
            + ' with the name ' + (self.manager).name)


class polyTypedVariable(treeObject):
    @treeObjectInit
    def __init__(self, polyTypedObj=None, attributeName=None, attributeValue=None):
        #The name of the variable in the class
        self.polyTypedObj = polyTypedObj
        self.name = attributeName
        #if(polyTypedObj == 'testObj'):
        #    print('Making testObj on polariServer for variable: ', attributeName)
        #Breaks down a data type into the programming language name of the data type,
        #the datatype defined for it, and the number of symbols (regardless of type)
        #that must be used in order to define it.
        dataType = type(attributeValue).__name__
        self.eventsList = []
        #Accounts for different set-like data types and what may be contained inside.
        if(callable(attributeValue)):
            self.eventsList.append(attributeValue)
        if(dataType == 'list' or dataType == 'tuple' or dataType == 'dict'):
            dataType = self.extractSetTyping(varSet=attributeValue)
        elif(not dataType in dataTypesPython and dataType != 'NoneType' and dataType != 'method'):
            #Find the definition of the object for the given manager, and construct based on that.
            #Case where the object is not accounted for by the manager with a PolyTyping Instance.
            #print('Getting object of type, ', dataType, 'as an object.')
            obj = polyTypedObj.manager.getObjectTyping(classInstance=attributeValue)
            if(None == obj):
                obj = polyTypedObj.manager.makeDefaultObjectTyping(classInstance=attributeValue)
            polyTypedObj.addToObjReferenceDict(referencedClassObj=attributeValue.__class__, referenceVarName=self.name)
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
        if(setType == 'list' or setType == 'tuple'):
            for elem in varSet:
                elemType = type(elem).__name__
                if(elemType == 'list' or elemType == 'tuple' or elemType == 'dict'):
                    tempString = self.extractSetTyping(varSet=elem,typingString=typingString, curDepth = curDepth + 1, maxDepth=maxDepth)
                else:
                    tempString = elemType
                if(not tempString in typingString):
                    tempString += ','
                    typingString += tempString
        elif(setType == 'dict'):
            for elem in varSet.keys():
                elemType = type(elem).__name__
                if(elemType == 'list' or elemType == 'tuple' or elemType == 'dict'):
                    tempString = self.extractSetTyping(varSet=elem,typingString=typingString, curDepth = curDepth + 1, maxDepth=maxDepth)
                else:
                    tempString = elemType
                tempString += ':'
                elemType = type(varSet[elem]).__name__
                if(elemType == 'list' or elemType == 'tuple' or elemType == 'dict'):
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
        

    #MAKES A conversionTest Remote Event, which causes the data to be returned in
    #a response after it has been converted and before it has any operations performed
    #on it.
    #Detects a variable with a particular value to another language using default
    #conversions, then recieves that same value after it has been returned to python
    #both are analyzed as converted strings to assess if they are still the same value.
    #def isLosslessConversion(self, attributeTypingDict):
    #    define something here!!