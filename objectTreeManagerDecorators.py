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
from functools import wraps
from polyTyping import * 
from managedFiles import *
from managedExecutables import *
from managedDB import *
#from managedImages import *
from dataChannels import *
import types, inspect, base64

def managerObjectInit(init):
    #Note: For objects instantiated using this Decorator, MUST USER KEYWORD ARGUMENTS NOT POSITIONAL, EX: (manager=mngObj, id='base64Id')
    @wraps(init)
    def new_init(self, *args, **keywordargs):
        managerObject.__init__(self, *args, **keywordargs)
        new_init = init(self, *args, **keywordargs)
    return new_init

#Defines a Decorator @managerObject, which allocates all variables and functions necessary for
#an object to be a the manager object to an Object Tree.
class managerObject:
    def __init__(self, *args, **keywordargs):
        #Adding on the necessary variables for a manager object, in the case they are not defined.
        self.complete = False
        if not 'manager' in keywordargs.keys():
            setattr(self, 'manager', None)
        if not 'objectTyping' in keywordargs.keys():
            setattr(self, 'objectTyping', [])
        if not 'objectTree' in keywordargs.keys():
            #print('setting object tree')
            setattr(self, 'objectTree', None)
        if not 'managedFiles' in keywordargs.keys():
            setattr(self, 'managedFiles', [])
        if not 'id' in keywordargs.keys():
            setattr(self, 'id', None)
        if not 'db' in keywordargs.keys():
            setattr(self, 'db', None)
        if not 'polServer' in keywordargs.keys():
            setattr(self, 'polServer', None)
        if not 'subManagers' in keywordargs.keys():
            setattr(self, 'subManagers', [])
        if not 'idList' in keywordargs.keys():
            setattr(self, 'idList', [])
        if not 'branch' in keywordargs.keys():
            setattr(self, 'branch', self)
        print(self.idList)
        print('Assigning idList to ', self, '.')
        if not 'cloudIdList' in keywordargs.keys():
            setattr(self, 'cloudIdList', [])
        for name in keywordargs.keys():
            #print('In parameters, found attribute ', name, ' with value ', keywordargs[name])
            if(name=='manager' or name=='branch' or name=='id' or name=='objectTree' or name=='managedFiles' or name=='id' or name=='db' or name=='idList' or name=='cloudIdList' or name == 'subManagers' or name == 'polServer'):
                setattr(self, name, keywordargs[name])
        self.primePolyTyping()
        self.complete = True
        #new_init = init(self, *args, **keywordargs)
        self.makeObjectTree()
        if(self.id == None):
            self.makeUniqueIdentifier()
        

    def __setattr__(self, name, value):
        if(name == 'manager'):
            #TODO Write functionality to connect with a parent tree when/if manager is assigned.
            super(managerObject, self).__setattr__(name, value)
            return
        if(not hasattr(self,"complete") or (type(value).__name__ in dataTypesPython and type(value) != list)):
            super(managerObject, self).__setattr__(name, value)
            return
        if(not self.complete):
            super(managerObject, self).__setattr__(name, value)
            return
        polyObj = self.getObjectTyping(self.__class__)
        selfTuple = self.getInstanceTuple(instance=self)
        #In polyObj 'polyObj.className' potential references exist for this object.
        #Here, we get each variable that is a reference or a list of references to a
        #particular type of object.
        if type(value) != list:
            if(value == None or value == []):
                pass
            else:
                accountedObjectType = False
                accountedVariableType = False
                if(type(value).__class__.__name__ in polyObj.objectReferencesDict):
                    accountedObjectType = True
                    print("Class type ", type(value).__class__.__name__, " accounted for in object typing for ", self.__class__.__name__)
                    if(polyObj.objectReferencesDict[type(value).__class__.__name__]):
                        accountedVariableType = True
                        print("Accounted for class type ", value, " as sole value in variable ", name)
                newpolyObj = self.getObjectTyping(classObj=value.__class__)
                managerPolyTyping = self.getObjectTyping(self.__class__)
                if(not accountedVariableType):
                    managerPolyTyping.addToObjReferenceDict(referencedClassObj=value.__class__, referenceVarName=name)
                ids = self.getInstanceIdentifiers(value)
                valuePath = self.getTuplePathInObjTree(instanceTuple=tuple([newpolyObj.className, ids, value]))
                if(valuePath == [selfTuple]):
                    #print("found an instance already in the objectTree at the correct location:", value)
                    #Do nothing, because the branch is already accounted for.
                    pass
                elif(valuePath == None):
                    #add the new Branch
                    print("Creating branch on manager for instance on variable ", name, " for instance: ", value)
                    newBranch = tuple([newpolyObj.className, ids, value])
                    self.addNewBranch(traversalList=[selfTuple], branchTuple=newBranch)
                    #Make sure the new branch has the current manager and the base as it's origin branch set on it.
                    if(self != value.branch):
                        value.branch = self
                    if(self != value.manager):
                        value.manager = self
                else:
                    #add as a duplicate branch
                    #print("Found an instance at a higher level which is now being moved to be a branch on the managed: ", value)
                    duplicateBranchTuple = tuple([newpolyObj.className, ids, tuple(valuePath)])
                    self.replaceOriginalTuple(self, originalPath=valuePath, newPath=[selfTuple,duplicateBranchTuple], newTuple=duplicateBranchTuple)
                    #Make sure the new branch has the current manager and the base as it's origin branch set on it.
                    if(value.branch != self):
                        value.branch = self
                    if(self != value.manager):
                        value.manager = self
        elif(type(value) == list):
            print("Accounting for setting elements in list on variable \'", name, "\' on the manager object.")
            #Adding a list of objects
            for inst in value:
                accountedObjectType = False
                accountedVariableType = False
                if(type(inst).__class__.__name__ in polyObj.objectReferencesDict):
                    accountedObjectType = True
                    print("Class type ", type(inst).__class__.__name__, " accounted for in object typing for ", self.__class__.__name__)
                    if(polyObj.objectReferencesDict[type(inst).__class__.__name__]):
                        accountedVariableType = True
                        print("Accounted for class type ", inst, " as sole value in variable ", name)
                newpolyObj = self.getObjectTyping(classObj=inst.__class__)
                managerPolyTyping = self.getObjectTyping(self.__class__)
                if(not accountedVariableType):
                    managerPolyTyping.addToObjReferenceDict(referencedClassObj=inst.__class__, referenceVarName=name)
                ids = self.getInstanceIdentifiers(inst)
                instPath = self.getTuplePathInObjTree(instanceTuple=tuple([newpolyObj.className, ids, inst]))
                if instPath == []:
                    #print("found an instance already in the objectTree at the correct location:", inst)
                    pass
                elif instPath == None:
                    print("Creating branch on manager for instance in list on variable ", name, " for instance: ", inst)
                    newBranch = tuple([newpolyObj.className, ids, inst])
                    self.addNewBranch(traversalList=[selfTuple], branchTuple=newBranch)
                    #Make sure the new branch has the current manager and the base as it's origin branch set on it.
                    if(self != inst.branch):
                        inst.branch = self
                    if(self != inst.manager):
                        inst.manager = self
                else:
                    #print("Found an instance at a higher level which is now being moved to be a branch on the managed: ", inst)
                    duplicateBranchTuple = tuple([newpolyObj.className, ids, tuple(instPath)]) 
                    self.replaceOriginalTuple(self, originalPath = instPath, newPath=[selfTuple,duplicateBranchTuple], newTuple=duplicateBranchTuple)
                    #Make sure the new branch has the current manager and the base as it's origin branch set on it.
                    if(self != inst.branch):
                        inst.branch = self
                    if(self != inst.manager):
                        inst.manager = self
        else:
            #print('Setting attribute to a value: ', value)
            print('Found object: "', value ,'" being assigned to an undeclared reference variable: ', name, 'On object: ', self)
            newpolyObj = self.getObjectTyping(classObj=value.__class__)
            managerPolyTyping = self.getObjectTyping(self.__class__)
            managerPolyTyping.addToObjReferenceDict(referencedClassObj=value.__class__, referenceVarName=name)
            print('Setting attribute on manager using a new polyTyping: ', newpolyObj.className, '; and set manager\'s new reference dict: ', managerPolyTyping.objectReferencesDict)
            print(newpolyObj.className, 'object placed on manager ', self,' it\'s referenceDict after allocation is: ', newpolyObj.objectReferencesDict)
            #if(self.identifiersComplete(value)):
            ids = self.getInstanceIdentifiers(value)
            valuePath = self.getTuplePathInObjTree(instanceTuple=tuple([newpolyObj.className, ids, value]))
            if(valuePath == [selfTuple]):
                #print("found an instance already in the objectTree at the correct location:", value)
                #Do nothing, because the branch is already accounted for.
                pass
            elif(valuePath == None):
                #add the new Branch
                print("Creating branch on manager for variable ", name," for instance: ", value)
                newBranch = tuple([newpolyObj.className, ids, value])
                self.addNewBranch(traversalList=[selfTuple], branchTuple=newBranch)
                #Make sure the new branch has the current manager and the base as it's origin branch set on it.
                if(self != value.branch):
                    value.branch = self
                if(self != value.manager):
                    value.manager = self
            else:
                #add as a duplicate branch
                #print("Found an instance at a higher level which is now being moved to be a branch on the managed: ", value)
                duplicateBranchTuple = tuple([newpolyObj.className, ids, tuple(valuePath)])
                self.replaceOriginalTuple(self, originalPath=valuePath, newPath=[selfTuple,duplicateBranchTuple], newTuple=duplicateBranchTuple)
                #Make sure the new branch has the current manager and the base as it's origin branch set on it.
                if(self != value.branch):
                    value.branch = self
                if(self != value.manager):
                    value.manager = self
        #print("Finished setting value of ", name, " to be ", value)
        super(managerObject, self).__setattr__(name, value)

    #If the Object's PolyTypedObject exists on the given manager object
    def getObjectTyping(self, classObj=None, className=None, classInstance=None ):
        if className != None:
            for objType in self.objectTyping:
                if(objType.className == className):
                    return objType
        elif classInstance != None:
            for objType in self.objectTyping:
                if(objType.className == classInstance.__class__.__name__):
                    return objType
        elif classObj != None:
            for objType in self.objectTyping:
                if(objType.className == classObj.__name__):
                    return objType
        else:
            print("You called the \'getObjectTyping\' function without passing any parameters!  Must pass one of the three parameter options, the string name of the class, an instance of the class, or the class defining object itself \'__class__\'.")
        obj = None
        if className != None:
            print("Attempted to retrieve a polyTypedObject that does not exist \"", className, "\" using it\'s name as a string.  Cannot generate a default polyTypedObject using a passed string, pass either an object instance or the class object \'__class__\' to generate a default polyTypedObject.")
        elif classInstance != None:
            if(classInstance.__class__.__name__ == 'polyTypedObject' or classInstance.__class__.__name__ == 'polyTypedVar'):
                print('Trying to create typing for polyTyping when it should already exist.')
            else:
                obj = self.makeDefaultObjectTyping(classInstance=classInstance)
        elif classObj != None:
            if(classObj.__name__ == 'polyTypedObject' or classObj.__name__ == 'polyTypedVar'):
                print('Trying to create typing for polyTyping when it should already exist.')
            else:
                obj = self.makeDefaultObjectTyping(classObj=classObj)
        return obj

    #
    def getListOfInstancesAtDepth(self, target_depth, depth=0, traversalList=[], source=None):
        #print("In \'getListOfClassInstances\' branch with traveral list : ", traversalList)
        if(source==None):
            source = self
            print("Source set as: ", self)
        #else:
        #    return source.getListOfClassInstances(className=className, traversalList=traversalList, source=source)
        ids = self.getInstanceIdentifiers(source)
        #print('Ids of Source: ', ids)
        #print('Class Name of Source: ', source.__class__.__name__)
        #print('Current Traversal List: ', traversalList)
        sourceTuple = tuple([source.__class__.__name__, ids, source])
        instanceList = []
        tempList = []
        if(traversalList != None):
            branch = self.getBranchNode(traversalList = traversalList)
            #print('Retrieving Branch for traversal List \"', traversalList, '\" : ', branch)
            #Handles the case for when we are on a duplicate branch.
            if(branch == None):
                instanceList = []
            else:
                for branchTuple in branch.keys():
                    #print('Searching tuple of class: ', branchTuple[0])
                    if(depth == target_depth):
                        #print("Found a match for the class ", className, " in the manager object ", self, ", the matched object was ", branchTuple[2])
                        instanceList.append(branchTuple[2])
                    #else:
                        #print("A non-matching object was found, ", branchTuple[2])
                for branchTuple in branch.keys():
                    tempList = self.getListOfInstancesAtDepth(target_depth=target_depth, depth=depth+1, traversalList=traversalList+[branchTuple], source=source)
                    instanceList = instanceList + tempList
        else:
            #print('source object does not exist in the object tree of manager object, returning empty list of objects.')
            instanceList = []
        return instanceList

    #Retrieves the source file for a given PolyTyped object for a given coding language, with the default set as python language.
    def getObjectTypingClassFile(self, className, language='py'):
        for objType in self.objectTyping:
            if(objType.className == className):
                #print('Found typing for object ', className, ' the typing object is ', objType)
                if(objType.sourceFiles != None and objType.sourceFiles != []):
                    #print(objType.sourceFiles)
                    for srcFile in objType.sourceFiles:
                        if(srcFile.extension == language):
                            return srcFile
        return None

    #
    def getListOfClassInstances(self, className, traversalList=[], source=None):
        #print("In \'getListOfClassInstances\' branch with traveral list : ", traversalList)
        if(source==None):
            source = self
            print("Source set as: ", self)
        #else:
        #    return source.getListOfClassInstances(className=className, traversalList=traversalList, source=source)
        ids = self.getInstanceIdentifiers(source)
        #print('Ids of Source: ', ids)
        #print('Class Name of Source: ', source.__class__.__name__)
        #print('Current Traversal List: ', traversalList)
        sourceTuple = tuple([source.__class__.__name__, ids, source])
        instanceList = []
        tempList = []
        if(traversalList != None):
            branch = self.getBranchNode(traversalList = traversalList)
            #print('Retrieving Branch for traversal List \"', traversalList, '\" : ', branch)
            #Handles the case for when we are on a duplicate branch.
            if(branch == None):
                instanceList = []
            else:
                for branchTuple in branch.keys():
                    #print('Searching tuple of class: ', branchTuple[0])
                    if(branchTuple[0] == className):
                        #print("Found a match for the class ", className, " in the manager object ", self, ", the matched object was ", branchTuple[2])
                        instanceList.append(branchTuple[2])
                    #else:
                        #print("A non-matching object was found, ", branchTuple[2])
                for branchTuple in branch.keys():
                    tempList = self.getListOfClassInstances(className=className, traversalList=traversalList+[branchTuple], source=source)
                    instanceList = instanceList + tempList
        else:
            #print('source object does not exist in the object tree of manager object, returning empty list of objects.')
            instanceList = []
        return instanceList

    #Creates a polyTypedObject instance for an object where the object is not
    #properly defined, then returns the new polyTypedObject.
    def makeDefaultObjectTyping(self, classInstance=None, classObj=None):
        #First, make sure to double check that the polyTyping does not already exist.
        if(classInstance != None):
            for someTypingObj in self.objectTyping:
                if(someTypingObj.className == classInstance.__class__.__name__):
                    return someTypingObj
        elif(classObj != None):
            for someTypingObj in self.objectTyping:
                if(someTypingObj.className == classObj.__name__):
                    return someTypingObj
        isBuiltinClass = False
        try:
            if(classInstance != None):
                classDefiningFile = inspect.getfile(classInstance.__class__)
            elif(classObj != None):
                classDefiningFile = inspect.getfile(classObj)
            else:
                print("Called \'makeDefaultObjectTyping\' without passing either a class instance or object for reference, no polyTypedObject could be generated.")
            pass
        except:
            print('Caught exception for retrieving file, thereby instance of type', classInstance.__class__.__name__ , ' with a value of ', classInstance,' must be a built-in class')
            isBuiltinClass = True
            pass
        if(isBuiltinClass):
            sourceFiles = []
        else:
            dotIndex = classDefiningFile.index(".")
            classDefiningFile = classDefiningFile[0:dotIndex]
            sourceFiles = [classDefiningFile]
            print('Class file name: ', classDefiningFile)
        if(classInstance != None):
            classDefaultTyping = polyTypedObject(manager=self, sourceFiles=sourceFiles, className=classInstance.__class__.__name__, identifierVariables=['id'])
            #return classDefaultTyping
        elif(classObj != None):
            classDefaultTyping = polyTypedObject(manager=self, sourceFiles=sourceFiles, className=classObj.__name__, identifierVariables=['id'])
            #return classDefaultTyping
        if(classInstance != None):
            if(classInstance.__class__.__name__ != 'list'):
                classDefaultTyping.analyzeInstance(classInstance)
            else:
                for inst in classInstance:
                    classDefaultTyping.analyzeInstance(inst)
        self.objectTyping.append(classDefaultTyping)
        return classDefaultTyping

    

    #Returns True if the identifiers for the object are fully defined, meaning it can be added to the object tree and save properly.
    #Returns False if any identifiers are empty, indicating it is unfinished and will cause issues/conflicts if it were to be saved or placed in the object tree.
    def identifiersComplete(self, instance):
        idTuples = self.getInstanceIdentifiers(instance=instance)
        for idTup in idTuples:
            if(idTup[1] == None or idTup[1] == []):
                return False
        return True

    def getInstanceIdentifiers(self, instance):
        isValid = False
        obj = None
        for parentObj in instance.__class__.__bases__:
            #print("Iterated Parent object in getInstanceIdentifiers: ", parentObj.__name__)
            if(parentObj.__name__ == "treeObject" or parentObj.__name__ == "managerObject"):
                isValid = True
        #If it is a valid object then we retrieve the object typing, otherwise we let it fail by not defining obj.
        if(isValid):
            obj = self.getObjectTyping(classInstance=instance)
        else:
            print("Invalid instance value sent to getInstanceIdentifiers: ", instance)
        if(obj == None):
            #print('No object found while getting instance identifiers')
            return None
        idVars = obj.identifiers
        #Compiles a dictionary of key-value pairs for the identifiers 
        identifiersDict = {}
        for id in idVars:
            try:
                identifiersDict[id] = getattr(instance,id)
            except AttributeError as error:
                print('For object ' + obj.__class__.__name__ + ' the list of identifiers is: ', idVars, 'Due to identifier missing, this error was thrown: ', error)
            listOfIdTuples = identifiersDict.items()
            identifiersTuplified = tuple(listOfIdTuples)
        return identifiersTuplified

    def getDuplicateInstanceTuple(self, instance):
            instanceTuple = self.getInstanceTuple(instance)
            path = self.getTuplePathInObjTree(instanceTuple)
            instanceTuple[2] = path
            return instanceTuple

    #Traverses the object tree to get a particular branch node by repeatedly accessing branches in-order according to the traversalList, 
    #which effectively acts as a path to the object acting as the branch
    def getBranchNode(self, traversalList):
        #print('Path passed in: ', traversalList)
        branch = self.objectTree
        for tup in traversalList:
            #print("Traversing tuple in path: ", tup)
            branch = branch[tup]
        #print('Branch Found: ', branch)
        return branch

    def getInstanceTuple(self, instance):
            return tuple([type(instance).__name__, self.getInstanceIdentifiers(instance), instance])

    #Returns a dictionary of all tuples of an instance, including tuples with paths and None
    #as well as the original.
    def getAllTuplesOfInstance(self, instanceTuple, traversalList=[]):
        pathDict = {"original":[],"noneDuplicates":[],"pathDuplicates":[]}
        branch = self.getBranchNode(traversalList = traversalList)
        #Handles the case where no further branches exist, meaning, it is currently on a duplicate Node.
        if(branch == None):
            return None
        path = None
        for branchTuple in branch.keys():
            if branchTuple[0] == instanceTuple[0] and branchTuple[1] == instanceTuple[1]:
                if(type(branchTuple[2]) == tuple):
                    pathDict["pathDuplicates"] = pathDict["pathDuplicates"] + [traversalList]
                elif(branchTuple[2] == None):
                    pathDict["noneDuplicates"] = pathDict["noneDuplicates"] + [traversalList]
                else:
                    pathDict["original"] = pathDict["original"] + [traversalList]
                return traversalList
        branchPathDict = {}
        for branchTuple in branch.keys():
            branchPathDict = self.getAllTuplesOfInstance(traversalList=traversalList+[branchTuple],instanceTuple=instanceTuple)
            pathDict["original"] = pathDict["original"] + branchPathDict["original"]
            pathDict["noneDuplicates"] = pathDict["noneDuplicates"] + branchPathDict["noneDuplicates"]
            pathDict["pathDuplicates"] = pathDict["pathDuplicates"] + branchPathDict["pathDuplicates"]
        return pathDict

    #Will go through every dictionary in the object tree and return branching depth of the tuple
    #if the tuple exists within the tree.
    def getTuplePathInObjTree(self, instanceTuple, traversalList=[]):
        #if(traversalList==[]):
        #    print('Trying to find Tuple match in Object Tree for tuple: ')
        #    print(instanceTuple)
        branch = self.getBranchNode(traversalList = traversalList)
        #Handles the case where no further branches exist, meaning, it is currently on a duplicate Node.
        if(branch == None):
            return None
        path = None
        #print('Branch to be searched: ', branch)
        for branchTuple in branch.keys():
            if branchTuple[0] == instanceTuple[0] and branchTuple[1] == instanceTuple[1]:
                #Case of a dup;icate match, where the path to the original is in the third position.
                if(type(branchTuple[2]) == tuple):
                    #print('Found tuple match!')
                    if(branchTuple[2] != [] and branchTuple[2] != None):
                        print("Returning non-empty path! - ", branchTuple[2])
                    return branchTuple[2]
                #Case of an exact match.
                elif(branchTuple[2] == instanceTuple[2]):
                    print("Found an exact match in the tree for instance: ", instanceTuple[2])
                    if(traversalList != [] and traversalList != None):
                        print("Returning non-empty path! - ", traversalList)
                    traversalList = traversalList + [branchTuple]
                    return traversalList
                #print('Found tuple match!')
                #print(traversalList)
                #return traversalList
        for branchTuple in branch.keys():
            path = self.getTuplePathInObjTree(traversalList=traversalList+[branchTuple],instanceTuple=instanceTuple)
            if(path != None):
                if(path != [] and path != None):
                    print("Returning non-empty path! - ", path)
                return path
        #if(traversalList == []):
        #    print('Tuple not found in tree!')
        #    print(instanceTuple)
        if(path != [] and path != None):
            print("Returning non-empty path! - ", path)
        return path

    #Access a single object instance as a node, and checks each typingObject to see what variables
    #that object has which may hold instances of other objects as either a instance or list of
    #instances, then returns all branches seperated into 3 categories "new","old", or "duplicates".
    #new: A branch with this class-identifiers combination does not exist in the tree at all.
    def getBranches(self, traversalList):
        branch = self.getBranchNode(traversalList=traversalList)
        #got branch node
        curTuple = traversalList[len(traversalList)-1]
        #Gets the name for the class of this branch from the tuple.
        classOfBranch = curTuple[0]
        oldBranches = []
        newBranches = []
        branchTuples = []
        duplicateBranchTuples = []
        #Goes through each object type used on the application and creates tuples
        for polyObj in self.objectTyping:
            if classOfBranch in polyObj.objectReferencesDict:
                #In polyObj 'polyObj.className' potential references exist for this object.
                #Here, we get each variable that is a reference or a list of references to a
                #particular type of object.
                for varName in polyObj.objectReferencesDict[classOfBranch]:
                    try:
                        value = getattr(curTuple[2], varName)
                    except:
                        print('Object References dictionary for object ', classOfBranch,': ', polyObj.objectReferencesDict)
                        print('trying to get value ', varName, ' from an instance ', curTuple[2], ' in polyObj ', polyObj.className, ' but attribute does not exist on object.')
                    #if(value == None or value == []):
                        #print(varName + ' is an empty variable for object ' + classOfBranch)
                    if(type(value) == list and not (value == None or value == [])):
                        #print('Entering variable with list: ' + varName)
                        #Adding a list of objects
                        for inst in value:
                            if(type(inst).__name__ == polyObj.className and self.identifiersComplete(inst)):
                                ids = self.getInstanceIdentifiers(inst)
                                instPath = self.getTuplePathInObjTree(instanceTuple=tuple([polyObj.className, ids, inst]))
                                if instPath == traversalList:
                                    oldBranches.append(tuple([polyObj.className, ids, inst]))
                                if instPath == None:
                                    newBranches.append( tuple([polyObj.className, ids, inst]) )
                                else:
                                    duplicateBranchTuples.append( tuple([polyObj.className, ids, tuple(instPath)]) )
                    else:
                        if(type(value).__name__ == polyObj.className and self.identifiersComplete(value)):
                            #Adding one object
                            ids = self.getInstanceIdentifiers(value)
                            valuePath = self.getTuplePathInObjTree(instanceTuple=tuple([polyObj.className, ids, value]))
                            if(valuePath == traversalList):
                                #as an old Branch
                                oldBranches.append( tuple([polyObj.className, ids, value])) 
                            elif(valuePath == None):
                                #as a new Branch
                                newBranches.append( tuple([polyObj.className, ids, value]))
                            else:
                                #as a duplicate branch
                                duplicateBranchTuples.append( tuple([polyObj.className, ids, tuple(valuePath)]) )
        return {"newBranches":newBranches,"oldBranches":oldBranches,"duplicates":duplicateBranchTuples}

    def makeObjectTree(self, traversalList=None, baseTuple=None):
        #print('making tree')
        if(traversalList == None or baseTuple== None):
            baseTuple=tuple([type(self).__name__, self.getInstanceIdentifiers(self), self])
            traversalList=[baseTuple]
            self.objectTree = {baseTuple:{}}
            #print('Tree Base Setup, getting Branches.')
        branchingDict = self.getBranches(traversalList)
        #print('Got Branches.')
        newBranches = branchingDict['newBranches']
        oldBranches = branchingDict['oldBranches']
        duplicates = branchingDict['duplicates']
        #When a new Branch has had all of it's sub-branches fully flushed out, it will be put
        #into the completeBranches list and removed from the newBranches list.
        completeBranches = []
        #When a duplicate is found, the duplicate and the current 'legitimate' reference will be
        #compared.  If the new duplicate has a branching depth less than the current existing
        #reference, then the new duplicate will replace the original.  After the comparison and
        #potential replacement, the duplicate is removed from duplicates and into accDuplicates
        #or rplDuplicates, if it had replaced a previously existing branch.
        accDuplicates = []
        rplDuplicates = []
        completionCount = 0
        iscomplete = False
        branchPulseComplete = False
        #print('before loop')
        while branchPulseComplete == False:
            if(newBranches != []):
                self.addNewBranch(traversalList=traversalList, branchTuple=newBranches[0])
                iscomplete = self.makeObjectTree(traversalList=traversalList+[newBranches[0]], baseTuple=baseTuple)
                if(iscomplete):
                    completionCount += 1
                newBranches.remove(newBranches[0])
            if(oldBranches != []):
                iscomplete = self.makeObjectTree(traversalList=traversalList+[oldBranches[0]], baseTuple=baseTuple)
                if(iscomplete):
                    completionCount += 1
                oldBranches.remove(oldBranches[0])
            if(duplicates != []):
                originalPath = self.getTuplePathInObjTree(instanceTuple=duplicates[0])
                #print("originalPath: ")
                #print(originalPath)
                #print("traversalPath: ")
                #print(traversalList)
                #If the newly generated Duplicate has a lower branching depth than the original,
                #then we replace the original with the new path.
                if(len(originalPath) > len(traversalList)):
                    self.replaceOriginalTuple(self, originalPath=originalPath, newPath=traversalList+[duplicates[0]], newTuple=duplicates[0])
                    iscomplete = self.makeObjectTree(traversalList=traversalList+[duplicates[0]], baseTuple=baseTuple)
                    if(iscomplete):
                        completionCount += 1
                    rplDuplicates.append(duplicates[0])
                if(len(originalPath) <= len(traversalList)):
                    self.addDuplicateBranch(traversalList=traversalList, branchTuple=duplicates[0])
                    completionCount += 1
                duplicates.remove(duplicates[0])
            if(newBranches == [] and oldBranches == [] and duplicates == []):
                branchPulseComplete = True
                #If it is the base of the tree, loop runs until all branches are complete.
                #Otherwise, after one branch pulse, everything is returned.
                if(traversalList != [tuple([type(self).__name__, self.getInstanceIdentifiers(self), self])]):
                    return False
                #Check to see if all branches are complete. 
        #print('Object Tree: ')
        #print(self.objectTree)
        return True

    #Accesses a branch node and adds a sub-branch to it, if the sub-branch does not already exist.
    def addNewBranch(self, traversalList, branchTuple=None, instance=None):
        if(len(traversalList) > 2):
            print("Trying to add new branch using traversalList of depth 3!! -> ", traversalList)
        if(instance != None):
            branchTuple = self.getInstanceTuple(instance)
        elif(branchTuple != None):
            instance = branchTuple[2]
        #Overwrites the traversal list in the case where the branch has already been defined.
        if(hasattr(instance, "branch")):
            if(instance.branch != None):
                parentBranchTuple = self.getInstanceTuple(instance.branch)
                traversalList = self.getTuplePathInObjTree(instanceTuple=parentBranchTuple)
        branchNode = self.getBranchNode(traversalList)
        branchingInstance = None
        try:
            if(traversalList != []):
                branchingInstance = traversalList[len(traversalList) - 1]
        except Exception:
            print("Error: In addNewBranch function, attempted to add new branch which returned invalid Node caused using invalid traversal list - ", traversalList)
        if(hasattr(instance, "manager")):
            if(instance.manager == self):
                pass
            elif(instance.manager == None):
                instance.manager = self
            else:
                instance.manager = self
                #TODO write code to delete branch from other manager and copy to this manager.
        if(hasattr(instance, "branch") and branchingInstance != None):
            if(instance.branch == traversalList[len(traversalList) - 1]):
                pass
            elif(instance.branch == None):
                instance.branch = traversalList[len(traversalList) - 1]
        if(traversalList[len(traversalList) - 1] != branchTuple):
            newTraversalList = traversalList + [branchTuple]
        if(traversalList == []):
            if(type(instance).__name__ == "treeBranchObject"):
                print("Attching treeBranchObject at base of tree?")
            self.objectTree[branchTuple] = {}
        elif(branchNode.get(branchTuple) == None):
            print("Adding new node in addNewBranch on sub-path's tuple: ", traversalList[len(traversalList) - 1])
            branchNode[branchTuple] = {}

    #Accesses a branch node and adds an empty duplicate sub-branch, which contain identifiers and
    #the path to it's actual branch in the third element of it's tuple.
    def addDuplicateBranch(self, traversalList, branchTuple):
        branchNode = self.getBranchNode(traversalList)
        if(branchNode.get(branchTuple) == None):
            branchNode[branchTuple] = None

    def replaceOriginalTuple(self, originalPath, newPath, newTuple):
        #Get the new branch where this tuple is now going to rest
        newBranch = self.getBranchNode[newPath]
        originalBranch = self.getBranchNode[originalPath]
        originalTuple = None
        for branchTuple in originalBranch.keys():
            if(branchTuple[0]==newTuple[0] and branchTuple[1]==newTuple[1]):
                originalTuple = branchTuple
                break
        #Bring over all of the sub-branches that were attached to it to the new path.
        newBranch[originalTuple] = self.getBranchNode[originalPath+[originalTuple]]
        #Get the original path that the tuple was resting on.
        originalNode = self.getBranchNode[originalPath]
        #Remove the tuple and all of it's sub-branches which have already been moved.
        originalNode.remove(originalTuple)
        #Replace the tuple on the old branch with a 'duplicateTuple' that references the new path.
        replacementTuple = tuple([originalTuple[0], originalTuple[1], originalPath])
        originalNode[replacementTuple] = None

    #Adds all of the basic objects that are necessary for the application to run, and accounts for
    #all of their identifiers.
    def primePolyTyping(self, identifierVariables=['id']):
        source_Polari = self.makeFile(name='definePolari', extension='py')
        source_dataStream = self.makeFile(name='dataStreams', extension='py')
        source_remoteEvent = self.makeFile(name='remoteEvents', extension='py')
        source_managedUserInterface = self.makeFile(name='managedUserInterface', extension='py')
        source_managedFile = self.makeFile(name='managedFiles', extension='py')
        #managedApp and browserSourcePage share the same source file.
        source_managedAppANDbrowserSourcePage = self.makeFile(name='managedApp', extension='py')
        source_managedDatabase = self.makeFile(name='managedDB', extension='py')
        source_dataChannel = self.makeFile(name='dataChannels', extension='py')
        source_managedExecutable = self.makeFile(name='managedExecutables', extension='py')
        source_polariServer = self.makeFile(name='polariServer', extension='py')
        #polyTyped Object and variable are both defined in the same source file
        source_polyTypedObject = self.makeFile(name='polyTyping', extension='py')
        source_polyTypedVars = self.makeFile(name='polyTypedVars', extension='py')
        self_module = inspect.getmodule(self.__class__)
        self_fileName = (self_module.__file__)[self_module.__file__.rfind('\\')+1:self_module.__file__.rfind('.')]
        self_path = (self_module.__file__)[:self_module.__file__.rfind('\\')]
        source_self = self.makeFile(name=self_fileName, extension='py', Path=self_path)
        print("source_self file name = ", self_fileName)
        print("source_self file path = ", self_path)
        self.objectTyping = [
            polyTypedObject(sourceFiles=[source_self], className=type(self).__name__, identifierVariables = identifierVariables, objectReferencesDict={}, manager=self),
            polyTypedObject(sourceFiles=[source_polyTypedVars], className='polyTypedVariable', identifierVariables = ['name','polyTypedObj'], objectReferencesDict={'polyTypedObject':['polyTypedVars']}, manager=self),
            polyTypedObject(sourceFiles=[source_Polari], className='Polari', identifierVariables = ['id'], objectReferencesDict={}, manager=self),
            polyTypedObject(sourceFiles=[source_dataStream], className='dataStream', identifierVariables = ['id'], objectReferencesDict={'managedApp':['dataStreamsToProcess','dataStreamsRequested','dataStreamsAwaitingResponse']}, manager=self),
            polyTypedObject(sourceFiles=[source_remoteEvent], className='remoteEvent', identifierVariables = ['id'], objectReferencesDict={'managedApp':['eventsToProcess','eventsToSend','eventsAwaitingResponse']}, manager=self),
            polyTypedObject(sourceFiles=[source_managedUserInterface], className='managedUserInterface', identifierVariables = ['id'], objectReferencesDict={'managedApp':['UIs']}, manager=self),
            polyTypedObject(sourceFiles=[source_managedFile], className='managedFile', identifierVariables = ['name','extension','Path'], objectReferencesDict={'managedApp':['AppFiles']}, manager=self),
            polyTypedObject(sourceFiles=[source_managedAppANDbrowserSourcePage], className='managedApp', identifierVariables = ['name'], objectReferencesDict={'managedApp':['subApps']}, manager=self),
            polyTypedObject(sourceFiles=[source_managedAppANDbrowserSourcePage], className='browserSourcePage', identifierVariables = ['name','Path'], objectReferencesDict={'managedApp':['landingSourcePage','sourcePages']}, manager=self),
            polyTypedObject(sourceFiles=[source_managedDatabase], className='managedDatabase', identifierVariables = ['name','Path'], objectReferencesDict={'managedApp':['DB']}, manager=self),
            polyTypedObject(sourceFiles=[source_dataChannel], className='dataChannel', identifierVariables = ['name','Path'], objectReferencesDict={'polariServer':['serverChannel'],'managedApp':['serverChannel','localAppChannel']}, manager=self),
            polyTypedObject(sourceFiles=[source_managedExecutable], className='managedExecutable', identifierVariables = ['name', 'extension','Path'], objectReferencesDict={}, manager=self),
            polyTypedObject(sourceFiles=[source_polyTypedObject], className='polyTypedObject', identifierVariables = ['className'], objectReferencesDict={self.__class__.__name__:['objectTyping']}, manager=self),
            polyTypedObject(sourceFiles=[source_polariServer], className='polariServer', identifierVariables = ['name', 'id'], objectReferencesDict={}, manager=self)
        ]
        #Goes through the objectTyping list to make sure that the object
        #that is 'self' was accounted for, adds a default typing if not.
        selfIsTyped = False
        for objTyp in self.objectTyping:
            if(objTyp.className == type(self).__name__):
                self.makeDefaultObjectTyping(objTyp)
                selfIsTyped = True
            if(objTyp.className == 'polyTypedObject'):
                for typingInst in self.objectTyping:
                    objTyp.analyzeInstance(typingInst)
                for typingInst in self.objectTyping:
                    for typedVar in typingInst.polyTypedVars:
                        objTyp.analyzeInstance(typedVar)
        if not selfIsTyped:
            source_self = self.makeFile(name=self.__class__.__module__, extension='py')
            self.addObjTyping(sourceFiles=[source_self], className=type(self).__name__, identifierVariables=identifierVariables, objectReferencesDict={})
            #self.makeDefaultObjectTyping(objTyp)

    def addObjTyping(self, sourceFiles, className, identifierVariables, objectReferencesDict={}):
        foundObj = False
        for objTyp in self.objectTyping:
            if(objTyp.className == className):
                foundObj = True
        if(not foundObj):
            newTypingObj = polyTypedObject(sourceFiles=sourceFiles, className=className, identifierVariables=identifierVariables, objectReferencesDict=objectReferencesDict, manager=self)
        

    def makeFile(self, name=None, extension=None, Path = None):
        #print('Entered makefile function')
        if extension in fileExtensions:
            newFile = managedFile(name=name, extension=extension, Path = Path)
        elif extension in picExtensions:
            newFile = managedImage(name=name, extension=extension, Path = Path)
        elif extension in dataBaseExtensions:
            newFile = managedDatabase(name=name, Path = Path)
        elif extension in dataCommsExtensions:
            newFile = dataChannel(name=name, Path = Path)
        elif extension in executableExtensions:
            newFile = managedExecutable(name=name, extension=extension, Path = Path)
        newFile.openFile()
        (self.managedFiles).append(newFile)
        return newFile

    #In the case where this object is a Subordinate Object tree,
    #it should reference the highest order manager to establish it's id.
    def makeUniqueIdentifier(self, N=9):
        import random
        if(self.manager == None):
            self.id = None
            return
        else:
            idString = ''
            for i in range(0,N):
                num = random.randint(0,63)
                idString += numToBase64(num = num)
            if(not idString in self.idList):
                self.id = idString
                (self.idList).append(idString)
                return
            else:
                self.id = self.makeUniqueIdentifier(self, N=N+1)
                return
        

    def numToBase64(self, num):
        byteNum = num.encode('ascii')
        b64Num = base64.b64encode(byteNum)
        return b64Num


    #Types of operations on queries that can narrow down search criteria.
    #Strict criteria run first because they narrow down options more quickly most consistently.
    #relational criteria run second because they often narrow down options more than a subSet operation.
    #subSet criteria run last because they 
    #strict criteria (very restrictive) - Narrows to instances which carry only one specific value for a var.
    #relational criteria (variably restrictive) - Narrows to instances which are determined to have a relation (Immediate connection through Object Tree) with a specified object.
    #subSet criteria (less restrictive) - Narrows all instances down to a subset of possibilities of itself based on criteria.
    #STRICT OPERATION TYPES TABLE
    #max - gets instances in tree holding the maximum numeric value for that variable.
    #min - gets instances in tree holding the minimum numeric value for that variable.
    # == - gets instances where the variable has the exact value entered.
    # SUBSET CRITERIA TYPES TABLE
    # >,<,>=,<= - gets instances in tree based on numeric value in comparison to a specified value being compared.
    #%+ - gets instances which have a post-fix matching the given specifier, and may have anything following that.
    #+% - gets instances which have a pre-fix matching the given specifier
    #+%+ - gets instances where any portion of the variables value matches the specifier
    strictOperationTypes = [("max"),("min"),("==","var")]
    WITHrelationalOperationTypes = [("hasChildren","subQuery"),("hasParents","subQuery")]
    WHERErelationalOperationTypes = [("var","contains")]
    subSetOperationTypes = [("var","%","var"),(">","var"),("<","var"),(">=","var"),("<=","var"),("%","var"),("var","%")]
    WITHOperationTypes = strictOperationTypes + subSetOperationTypes
    specialCharacters = ["=",">","<"]
    orderingCharacters = [",","[","]","(",")",":"]
    #This function's only purpose is to retrieve instances from the system, and to give the system/user the ability to specify most any specific circumstance or criteria 
    #which one might want to use in order to narrow down their search for a specific set of instances,
    #as well as allowing them to chain criteria as much as desired, allowing maximum freedom.
    #SELECT section - If this section exists, the overall query will return a formatted json dictionary containing all converted objects with the specified variables included.
    #Example complex Object Tree query: queryString=
    #"[SELECT * FROM testObj WITH { id:(max), testVar:(=None), name:(a%c%), objList:( contains[ FROM secondTestObj WITH { name:(='name') } ] ) } WHERE hasChildren:[ FROM secondTestObj ]")
    #This would return a json dictionary of testObj
    def queryObjectTree(self, queryString): 
        curType = None
        idName = None
        #make all letters in the query lowercase to ensure uniformity.
        queryString = queryString.lower()
        queryStartIndex = queryString.find('[')
        queryEndIndex = queryString.rfind(']')
        queryString = queryString.substring(queryStartIndex + 1, queryEndIndex - 1)
        #if()
        SELECTstring = ""
        FROMstring = ""
        WITHstring = ""
        WHEREstring = ""
        tempTuple = []
        tuplesList = []
        strictCommands = []
        subSetCommands = []
        subQueries = []
        relationalCommands = []
        varQuery = {}
        #Parsing Commands and putting them in appropriate order
        for objType in (self.manager).objectTyping:
            if(objType.className == className):
                curType = objType
                break
        if(curType == None):
            print("Object Type (Polytyping Object) not defined on the given manager object for type - ", curType)
            return
        #Parse through and eliminate all spaces, then get variable query sets
        i = 0
        varName = None
        cmdFound = False
        #Go through the query and convert the query into a list of query commands
        #sorted into strict, subSet, and relational sections, and assign a specific
        #variable to perform each operation on and specified variables to utilize within
        #the operation to narrow down allowed values.
        curVar = None
        while i < len(queryString):
            cmdFound = False
            #Skip over any spaces
            if(queryString[i] == ' '):
                continue
            #A variable has been loaded and now we are iterating through criteria that must be met or analyzed in regards to that specific variable.
            elif(curVar != None):
                if(queryString[i]==')'):
                    varDict['criteriaEndIndex'] = i
                    curVar == None
                    continue
                for cmdTuple in WITHOperationTypes:
                    if(cmdTuple[0] == 'var'):
                        cmd = cmdTuple[1]
                    else:
                        cmd = cmdTuple[0]
                    j = 0
                    while j < len(cmd):
                        if((cmd)[j:j+1] == queryString[i+j]):
                            if(j == len(cmd) - 1):
                                if(queryString[i:i+j] in strictOperationTypes):
                                    strictCommands.append( tuple([]) )
                                elif(queryString[i:i+j] in subSetOperationTypes):
                                    subSetCommands.append( tuple([]) )
                                elif(queryString[i:i+j] in relationalOperationTypes):
                                    relationalCommands.append( tuple([]) )
                                else:
                                    print('Error: Could not find type for command.')
                                cmdFound = True
                                i = i + j
                                break
                        else:
                            break
                        j += 1
            #looks to see if this may be the first character of a command
            elif(curVar == None):
                foundKeyChar = False
                j = 0
                while (not foundKeyChar) or i+j < len(queryString):
                    if(queryString[i+j] in orderingCharacters):
                        if(queryString[i+j:i+j+2] == ":("):
                            #Get the word before this ':', which should be the variable name, load it onto varName.
                            k = 0
                            endSpaceIndexes = []
                            wordStartFound = False
                            lowestSpcIndex = None
                            while not wordStartFound:
                                if(queryString[i+j-k] == ' '):
                                    if(k == 1):
                                        lowestSpcIndex = k
                                    elif(k == lowestSpcIndex+1):
                                        lowestSpcIndex = k
                                elif(queryString[i+j-k] == '[' or ','):
                                    l = 1
                                    while(i+j-k+l):
                                        if(queryString[i+j-k+l]!=' '):
                                            wordStartFound = True
                                            startIndex= i+j-k+l
                                        l+=1
                                k+=1
                            varDict = {'varName':queryString[startIndex:i+j-(lowestSpcIndex+1)],'queryCriteriaCount':0,'criteriaStartIndex':i+j+2,'criteriaEndIndex':None}
                            varName = queryString[i:i+j-1]
                            i = (i+j+2)
                            break
                    j += 1
        if(not cmdFound):
            i += 1

    def parseSelect(startIndex, endIndex, queryString):
        selectionsDict = {}
        if(endIndex <= len(queryString)):
            i = startIndex
            while i < endIndex:
                #Skips through spaces that are not important in terms of notation
                if(queryString[i] == ' '):
                    i += 1
                    continue
                #catches notation within the query which would indicate a subquery, calculates
                #the logical equivolent WHERE operations based on the WHERE operations of the current
                #query.
                elif(queryString[i] == '['):
                    closerIndex = None
                    while i < endIndex and closerIndex==None:
                        if(queryString[i] == ']'):
                            closerIndex = i
                        i += 1
                
        return selectionsDict