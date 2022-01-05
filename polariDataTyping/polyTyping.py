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
#from polariAI.definePolari import *
#from polariFrontendManagement.managedApp import *
from polariApiServer.remoteEvents import *
from objectTreeDecorators import *
from  polariDataTyping.polyTypedVars import *
from inspect import signature
#from polariAnalytics.functionalityAnalysis import *
import logging, os, sys, importlib

#Accounts for data on a class and allows for valid data typing in multiple types,
#also accounts for the conversion of data types that should be performed when
#transmitting data across environments and into other programming language contexts.
class polyTypedObject(treeObject):
    @treeObjectInit
    def __init__(self, className, manager, objectReferencesDict={}, sourceFiles=[], identifierVariables=[], variableNameList=[], baseAccessDict={}, basePermDict={}, classDefinition=None, sampleInstances=[], kwRequiredParams=[], kwDefaultParams={}):
        #if(className == 'polariServer'):
        #    print('Making the polyTyping object for polariServer with manager set as: ', manager)
        self.isTreeObject = None
        self.isManagerObject = None
        self.className = className
        self.kwRequiredParams = []
        self.kwDefaultParams = []
        self.hasBaseSample = False
        #The list of objects that have variables which reference this object, either as a single
        #instance, or as a list of the instances.
        self.objectReferencesDict = objectReferencesDict
        if(sampleInstances != []):
            paramsSample =  signature(sampleInstances[0].__class__.__init__)
            self.kwRequiredParams = []
            self.kwDefaultParams = []
            for keywordParam, kwWithvalue in paramsSample.parameters.items():
                if(str(kwWithvalue).find("=") != -1):
                    self.kwDefaultParams.append(str(keywordParam))
                else:
                    self.kwRequiredParams.append(str(keywordParam))
            print("params for ",className,": ", paramsSample)
        elif(classDefinition != None):
            paramsSample =  signature(classDefinition.__init__)
            self.kwRequiredParams = []
            self.kwDefaultParams = []
            for keywordParam, kwWithvalue in paramsSample.parameters.items():
                if(str(kwWithvalue).find("=") != -1):
                    self.kwDefaultParams.append(str(keywordParam))
                else:
                    self.kwRequiredParams.append(str(keywordParam))
        if(kwRequiredParams != []):
            self.kwRequiredParams = kwRequiredParams
        if(kwDefaultParams != []):
            self.kwDefaultParams = kwDefaultParams
        if(kwRequiredParams == [] and kwDefaultParams == []):
            self.kwRequiredParams = kwRequiredParams
            self.kwDefaultParams = kwDefaultParams
        #A dictionary of required keyword parameters.
        self.requiredInitKeywordParams = []
        #A dictionary of keyword parameters with defaults.
        self.initKeywordParamsWdefaults = {}
        #A list of managed files that defined this class for different languages.
        #print('passed source files: ', sourceFiles)
        self.sourceFiles = sourceFiles
        #
        self.polariSourceFile = None
        for someSrc in self.sourceFiles:
            if(someSrc.__class__.__name__ != 'managedFile' and someSrc.__class__.__name__ != 'managedExecutable'):
                errMsg = "Sourcefiles for class type " + className + " found to contain an invalid value in sourceFiles list: "+ someSrc + " of type "+ someSrc.__class__.__name__ +"  All values must be of type managedFile or managedExecutable."
                raise ValueError(errMsg)
            if(someSrc.extension == 'py'):
                self.polariSourceFile = someSrc
                #print("Set polari Source file for class", self.className," to value: ", someSrc)
                break
        if(self.polariSourceFile == None):
            print("No python/polari source file could be found for the class type: ", self.className)
        #The context (App or Polari) in which this Object is being utilized
        self.manager = manager
        if(manager != None):
            manager.objectTypingDict[className] = self
        #The instances of this object's polyTyping in higher tiered contexts.
        self.inheritedTyping = []
        #Variables that may be used as unique identifiers.
        if(identifierVariables == [] or identifierVariables == ['id']):
            self.identifiers = ['id']
        elif(type(identifierVariables).__name__ == 'list' or type(identifierVariables).__name__ == 'polariList'):
            self.identifiers = identifierVariables
        else:
            #This should probably throw an error, but I'll just be nice and autocorrect it to the default if someone messes things up for now.
            self.identifiers = ['id']
        #The names of all of the Variables for the class.
        self.variableNameList = variableNameList
        #The polyTypedVariable instances for each of the variables in the class.
        self.polyTypedVars = []
        #
        self.baseAccessDictionary = {}
        self.basePermissionDictionary = {}

    #Go through each instance and analyze it.
    def runAnalysis(self):
        allInstances = self.manager.getListOfClassInstances(self.className)
        for inst in allInstances:
            self.analyzeInstance(inst)

    def makeDefaultPermissionSets(self):
        #ACCESS PERMISSION SETS
        #Allows User to perform GET requests on all existing object instances of this class.
        #By default this also gives readAllVarsPS. 
        accessAllPS = polariPermissionSet(apiObject=self.className, Name="Access All Instances")
        #Allows User to perform GET, PUT, and POST requests on all objects where the self.owner value
        #is either the given User themselves or a group which they are able to be determined to
        #belong to.  By default this is a super-set of the readAllVarsPS & the updateAllVarsPS.
        accessOwnershipPS = polariPermissionSet(apiObject=self.className, Name="Owner-based Instance Access")
        #FUNCTIONS ON PERMISSION SETS
        #Allows user to call any function on an object instance using a POST request or custom request type.
        runAllFunctionsPS = polariPermissionSet(apiObject=self.className, Name="Run Functions on Instance")
        #CREATE PERMISSION SETS
        #Allows a user to create an object instance and automatically set them to be the owner.
        createAsOwner = polariPermissionSet(apiObject=self.className, Name="Create as owner")
        #Allows a user to create an object instance which by default is them but can be changed to someone else
        #so long as they also have at least ownershipPS for the given object.
        createAndEditOwner = polariPermissionSet(apiObject=self.className, Name="Create and assign owner")
        #Allows a user to create an object instance, but not assign an owner for that instance, is used for objects
        #which would assign ownership automatically at creation or are always ownerless and available universally.
        createOwnerless = polariPermissionSet(apiObject=self.className, Name="Create without assigning an owner")
        #READ PERMISSION SETS
        readAllVarsPS = polariPermissionSet(apiObject=self.className, Name="Read All Variables")
        #UPDATE PERMISSION SETS
        updateAllVarsPS = polariPermissionSet(apiObject=self.className, Name="Update All Variables")
        #DELETE PERMISSION SETS
        #Allows ability for user to delete any instance user has access to.
        deleteAllPS = polariPermissionSet(apiObject=self.className, Name="Delete All Instances")
        #Allows ability for user to delete instances owned by the user.
        deleteOwnedPS = polariPermissionSet(apiObject=self.className, Name="Delete Owned Instances")


        

    #Where the object passed in is the value or values of the list of this polyTypedVariable,
    #we retrieve the key - self.polyTypedObject, from the objectReferencesDict of the passed in obj,
    #and ensure that our current variable's name is within the list which is the value owned by that key.
    def addToObjReferenceDict(self, referencedClassObj, referenceVarName):
        foundTyping = False
        if(referencedClassObj.__name__ == "polyTypedObject"):
            print("Changing reference dict on polyTyping after init")
            if(referenceVarName == "polyTypedObj"):
                print("For some reason trying to put polyTypedObj onto ref dict... not okay.")
                return
        if(hasattr(self, 'manager')):
            #print('Adding obj ', classObj, ' to object ref dict of ', self.className, ' for variable named: ', varName)
            for objType in self.manager.objectTyping:
                #Goes until objType == PolyTyping for object this variable belongs to.
                if(objType.className == referencedClassObj.__name__):
                    #The objectReference dictionary on the object's PolyTyping that the variable belongs to,
                    #with the key-value set to be the class of the value set on the variable.
                    #print("In addToObjReferenceDict for polyTyping of ", self.className," found typing for object ", objType.className, " for this typing adding variable ", referenceVarName)
                    foundTyping = True
                    if(not referencedClassObj.__name__ in objType.objectReferencesDict):
                        objType.objectReferencesDict[referencedClassObj.__name__] = [referenceVarName]
                    elif(not referenceVarName in objType.objectReferencesDict[referencedClassObj.__name__]):
                        (objType.objectReferencesDict[objType.className]).append(referenceVarName)
                    break
            if(not foundTyping):
                print("Never found typing in addToObjReferenceDict function for type ", referencedClassObj.__name__, " being allocated to variable ", referenceVarName)
                #TODO Create default typing if the typing does not exist.
        else:
            print('Attempting to set object reference on polyTyping object that has no manager assigned.')

    def checkIfManagerObject(self):
        if(hasattr(self, "isManagerObject")):
            if(self.isManagerObject == True):
                return True
            elif(self.isManagerObject == False):
                return False
        #print("Detecting if manager object type.")
        from polariFiles.managedFiles import managedFile
        for srcFile in self.sourceFiles:
            if( issubclass(srcFile.__class__, managedFile) or managedFile == srcFile.__class__):
                if(srcFile.extension == 'py'):
                    accessFile = srcFile
                    break
            else:
                print("For polyTyping on object \'", self.className, "\' found invalid non-managedFile type for sourcefile: ", srcFile)
                return False
        moduleImported = self.getCreateMethod()
        #print("Got create method: ", moduleImported)
        for name, obj in inspect.getmembers(moduleImported):
            #print("Iterating member - '", name, "' with a value - '", obj)
            if(name == self.className):
                from objectTreeManagerDecorators import managerObject
                if( issubclass(obj, managerObject) ):
                    self.isTreeObject = False
                    self.isManagerObject = True
                    return True
        return False

    def checkIfTreeObject(self):
        if(hasattr(self, "isTreeObject")):
            if(self.isTreeObject == True):
                return True
            elif(self.isTreeObject == False):
                return False
        from polariFiles.managedFiles import managedFile
        for srcFile in self.sourceFiles:
            if( issubclass(srcFile.__class__, managedFile) or managedFile == srcFile.__class__):
                if(srcFile.extension == 'py'):
                    accessFile = srcFile
                    break
            else:
                print("For polyTyping on object \'", self.className, "\' found invalid non-managedFile type for sourcefile: ", srcFile)
                return False
        moduleImported = self.getCreateMethod()
        for name, obj in inspect.getmembers(moduleImported):
            if(name == self.className):
                from objectTreeDecorators import treeObject
                if( issubclass(obj, treeObject) ):
                    self.isTreeObject = True
                    self.isManagerObject = False
                    return True
        return False
                

    #Creates typing for the instance by analyzing it's variables and creating
    #default polyTypedVariables for it.
    def analyzeInstance(self, pythonClassInstance):
        try:
            classInfoDict = pythonClassInstance.__dict__
            for someVariableKey in classInfoDict:
                if(someVariableKey == "polyTypedObj"):
                    #print("TRYING TO SET TYPE polyTypedObj in dict.. why?!?")
                    continue
                if(not callable(classInfoDict[someVariableKey])):
                    #print('accVar: ' + someVariableKey)
                    var = getattr(pythonClassInstance, someVariableKey)
                    #If the var is accounted for, analyze the current value.
                    self.analyzeVariableValue(pythonClassInstance=pythonClassInstance, varName=someVariableKey, varVal=var)
        except Exception:
            print('Invalid value of type ', type(pythonClassInstance).__name__,' in function analyzeInstance for parameter pythonClassInstance: ', pythonClassInstance)
        #print('Showing all polytyped Var for object ' + self.className + ': ', self.polyTypedVars)


    def analyzeVariableValue(self, pythonClassInstance, varName, varVal):
        #print('Analyzing variable ' + varName + ' in class ' + self.className)
        if(self.polyTypedVars == None):
            self.polyTypedVars = []
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

    def getCreateMethod(self, returnTupWithParams=False):
        #compares the absolute paths of this file and the directory where the class is defined
        #the first character at which the two paths diverge is stored into divIndex
        definingFile = self.polariSourceFile.name
        absDirPath = self.polariSourceFile.Path
        className = self.className
        if(absDirPath != None and definingFile != None and className != None):
            curPath =  (os.path.realpath(__file__))[:os.path.realpath(__file__).rfind('\\')]
            sIndex = curPath.rfind("\\")
            if(sIndex == -1):
                sIndex = curPath.rfind("/")
            curPath = curPath[:sIndex]
            divIndex = 0
            errMsg = "path to the file not in subdirectory of manager object.  Path to class must begin with: " + str(curPath) + ". Path entered was: " + str(absDirPath)
            charIndex = 0
            polariFrameworkPackageStartIndex = None
            polariFrameworkPackageEndIndex = None
            discrepencyIndex = None
            try:
                chars = range(len(absDirPath))
                for charIndex in chars:
                    if(absDirPath[charIndex] == curPath[charIndex]):
                        if( not (absDirPath[charIndex] == "\\" or absDirPath[charIndex] == "/") and  (curPath[charIndex] == "\\" or curPath[charIndex] == "/") ):
                            errMsg += " ERROR 0: discrepency read at index " + str(charIndex) + " base path character is " + curPath[charIndex] + " while file path character is " + absDirPath[charIndex]
                            raise ValueError(errMsg)
                    else:
                        discrepencyIndex = charIndex
                        break
                    if(charIndex == len(absDirPath) - 1):
                        break
                    if(charIndex == len(curPath) - 1):
                        break
                if(discrepencyIndex != 0 and discrepencyIndex != None):
                    reverseObjPathRange = range(len(absDirPath), 0, -1)
                    reverseTypingPathRange = range(len(curPath), 0, -1)
                    for someChar in reverseObjPathRange:
                        pass
            except:
                errMsg += " ERROR 2: Got exception at index " + str(charIndex)
                raise ValueError(errMsg)
            if(len(absDirPath) > len(curPath)):
                relativePath = absDirPath[len(curPath):]
                packageTraversalString = ""
                packageNameStartIndex = 0
                packageNameEndIndex = None
                if(relativePath[0] == "\\" or relativePath[0] == "/"):
                    packageNameStartIndex = 1
                    relativePathIndexing = range(1, len(absDirPath)-len(curPath)-1)
                else:
                    relativePathIndexing = range(len(absDirPath)-len(curPath)-1)
                for charIndex in relativePathIndexing:
                    if(relativePath[charIndex] == "\\" or relativePath[charIndex] == "/"):
                        packageNameEndIndex = charIndex - 1
                        curPackage = relativePath[packageNameStartIndex:packageNameEndIndex]
                        packageTraversalString += curPackage + "."
                        packageNameStartIndex = charIndex + 1
                if(packageNameStartIndex < len(absDirPath)-len(curPath)):
                    curPackage = relativePath[packageNameStartIndex:len(absDirPath)-len(curPath)]
                    packageTraversalString += curPackage + "."
                #Gets the subpath relative to the managedDatabase File
                #sys.path.append(relativePath)
                #Since the directory was adjusted we can now directly import the module from the subdirectory.
                definingPackage = packageTraversalString + definingFile
                absoluteImport = definingPackage+"."+className
                moduleImported = importlib.import_module(name=definingPackage)
                ClassInstantiationMethod = getattr(moduleImported, className)
                print("instantiation method from package: ", ClassInstantiationMethod)
                return ClassInstantiationMethod
            else:
                #Since the file is in the base/main directory, we import it directly
                moduleImported = __import__(name=definingFile, fromlist=className)
                ClassInstantiationMethod = getattr(moduleImported, className)
                return ClassInstantiationMethod
        else:
            errMsg = "Make sure to enter all three parameters into the makeTableByClass function!  Enter the"
            +"absolute directory path to the folder of the class to be made into a Database table first, then"
            + "enter the name of the file (without extension) where the class is defined second, then enter"
            +"the class name third."
            raise ValueError(errMsg)