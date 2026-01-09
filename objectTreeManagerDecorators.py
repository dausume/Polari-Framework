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
from polariDataTyping.polyTyping import * 
from polariFiles.managedFiles import *
from polariFiles.managedExecutables import *
from polariNetworking.defineLocalSys import isoSys
from polariDBmanagement.managedDB import *
from polariApiServer.polariServer import polariServer
#from polariFiles.managedImages import *
from polariDataTyping.polariList import polariList
from polariFiles.dataChannels import *
import types, inspect, base64, json, os, time

def managerObjectInit(init):
    #Note: For objects instantiated using this Decorator, MUST USER KEYWORD ARGUMENTS NOT POSITIONAL, EX: (manager=mngObj, id='base64Id')
    @wraps(init)
    def new_init(self, *args, **keywordargs):
        managerObject.__init__(self, *args, **keywordargs)
        initSig = inspect.signature(self.__init__)
        passableKeywargs = {}
        for param in initSig.parameters:
            if param in keywordargs:
                passableKeywargs[param] = keywordargs[param]
        new_init = init(self, *args, **passableKeywargs)
    return new_init

#Defines a Decorator @managerObject, which allocates all variables and functions necessary for
#an object to be a the manager object to an Object Tree.
class managerObject:
    def __init__(self, *args, **keywordargs):
        #Adding on the necessary variables for a manager object, in the case they are not defined.
        self.complete = False
        if not 'manager' in keywordargs.keys():
            setattr(self, 'manager', None)
        if not 'hostSys' in keywordargs.keys():
            setattr(self, 'hostSys', None)
        if not 'hasServer' in keywordargs.keys():
            setattr(self, 'hasServer', False)
        if not 'hasDB' in keywordargs.keys():
            setattr(self, 'hasDB', False)
        if not 'objectTyping' in keywordargs.keys():
            setattr(self, 'objectTyping', [])
        #TODO Plan to phase out access through objectTyping which requires looping with ObjectTypingDict
        #which is accessible through the class as a key for each typing object. (Need to keep list for API)
        if not 'objectTypingDict' in keywordargs.keys():
            setattr(self, 'objectTypingDict', {})
        if not 'objectTree' in keywordargs.keys():
            #print('setting object tree')
            setattr(self, 'objectTree', None)
        #TODO Plan to add functionality for additional 'flattened' or table-styled
        #object tree dictionary, which have two layers, the class layer which
        #indicates a 'table' and then the Id-tuples.  These tables can only hold
        #object instances which have had all Id fields filled out completely.
        #FORMAT: {'objectType0':{'polariId0':instance0, 'polariId1':instance1}}
        if not 'objectTables' in keywordargs.keys():
            setattr(self, 'objectTables', {})
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
        #print(self.idList)
        #print('Assigning idList to ', self, '.')
        if not 'cloudIdList' in keywordargs.keys():
            setattr(self, 'cloudIdList', [])
        for name in keywordargs.keys():
            #print('In parameters, found attribute ', name, ' with value ', keywordargs[name])
            if(name=='manager' or name=='branch' or name=='id' or name=='objectTables' or name=='objectTree' or name=='managedFiles' or name=='id' or name=='db' or name=='idList' or name=='cloudIdList' or name == 'subManagers' or name == 'polServer' or name == 'hasServer' or name == 'hostSys'):
                setattr(self, name, keywordargs[name])
        self.primePolyTyping()
        self.complete = True
        #new_init = init(self, *args, **keywordargs)
        self.makeObjectTree()
        if(self.id == None):
            self.makeUniqueIdentifier()
        if(self.hostSys == None):
            self.hostSys = isoSys(name="newLocalSys", manager=self)
        if(self.hasServer):
            self.polServer = polariServer(hostSystem=self.hostSys, manager=self)
        if(self.hasDB):
            self.db
        #Analyzing everything in base of tree
        if(self.__class__.__name__ in self.objectTypingDict):
            for someClass in self.objectTypingDict.keys():
                typeToAnalyze = self.objectTypingDict[someClass]
                typeToAnalyze.runAnalysis()

    def __delete__(self, instance):
        #TODO Go through all polyTyping objects and delete them, close all file references.
        #WRITE CODE HERE
        super(self.__class__, self).delete()
        

    def __setattr__(self, name, value):
        if(type(value).__name__ == 'list'):
            #if name == "usersList" -> converting from list with value ", value, " to a polariList.
            #Instead of initializing a polariList, we try to just cast the list to be type polariList.
            value = polariList(value)
            value.jumpstart(treeObjInstance=self, varName=name)
        if(name == 'manager'):
            #TODO Write functionality to connect with a parent tree when/if manager is assigned.
            super(managerObject, self).__setattr__(name, value)
            return
        if(not hasattr(self,"complete") or (type(value).__name__ in dataTypesPython and type(value) != list and type(value).__name__ != "polariList")):
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
        if type(value).__name__ != "list" and type(value).__name__ != "polariList":
            if(value == None or value == []):
                pass
            else:
                accountedObjectType = False
                accountedVariableType = False
                if(type(value).__class__.__name__ in polyObj.objectReferencesDict):
                    accountedObjectType = True
                    #print("Class type ", type(value).__class__.__name__, " accounted for in object typing for ", self.__class__.__name__)
                    if(polyObj.objectReferencesDict[type(value).__class__.__name__]):
                        accountedVariableType = True
                        #print("Accounted for class type ", value, " as sole value in variable ", name)
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
                    #print("Creating branch on manager for instance on variable ", name, " for instance: ", value)
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
        elif(type(value) == list or type(value).__name__ == "polariList"):
            #Adding a list of objects
            for inst in value:
                accountedObjectType = False
                accountedVariableType = False
                if(type(inst).__class__.__name__ in polyObj.objectReferencesDict):
                    accountedObjectType = True
                    #Class type, type(inst).__class__.__name__, accounted for in object typing for, self.__class__.__name__
                    if(polyObj.objectReferencesDict[type(inst).__class__.__name__]):
                        #Accounted for class type, inst, as sole value in variable, name
                        accountedVariableType = True
                newpolyObj = self.getObjectTyping(classObj=inst.__class__)
                managerPolyTyping = self.getObjectTyping(self.__class__)
                if(not accountedVariableType):
                    managerPolyTyping.addToObjReferenceDict(referencedClassObj=inst.__class__, referenceVarName=name)
                ids = self.getInstanceIdentifiers(inst)
                instPath = self.getTuplePathInObjTree(instanceTuple=tuple([newpolyObj.className, ids, inst]))
                if instPath == [selfTuple]:
                    #print("found an instance already in the objectTree at the correct location:", inst)
                    pass
                elif instPath == None:
                    #print("Creating branch on manager for instance in list on variable ", name, " for instance: ", inst)
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
        #else:
            #print('Setting attribute to a value: ', value)
            #print('Found object: "', value ,'" being assigned to an undeclared reference variable: ', name, 'On object: ', self)
            #newpolyObj = self.getObjectTyping(classObj=value.__class__)
            #managerPolyTyping = self.getObjectTyping(self.__class__)
            #managerPolyTyping.addToObjReferenceDict(referencedClassObj=value.__class__, referenceVarName=name)
            #print('Setting attribute on manager using a new polyTyping: ', newpolyObj.className, '; and set manager\'s new reference dict: ', managerPolyTyping.objectReferencesDict)
            #print(newpolyObj.className, 'object placed on manager ', self,' it\'s referenceDict after allocation is: ', newpolyObj.objectReferencesDict)
            #if(self.identifiersComplete(value)):
            #ids = self.getInstanceIdentifiers(value)
            #valuePath = self.getTuplePathInObjTree(instanceTuple=tuple([newpolyObj.className, ids, value]))
            #if(valuePath == [selfTuple]):
                #print("found an instance already in the objectTree at the correct location:", value)
                #Do nothing, because the branch is already accounted for.
            #    pass
            #elif(valuePath == None):
                #add the new Branch
                #print("Creating branch on manager for variable ", name," for instance: ", value)
            #    newBranch = tuple([newpolyObj.className, ids, value])
            #    self.addNewBranch(traversalList=[selfTuple], branchTuple=newBranch)
                #Make sure the new branch has the current manager and the base as it's origin branch set on it.
            #    if(self != value.branch):
            #        value.branch = self
            #    if(self != value.manager):
            #        value.manager = self
            #else:
                #add as a duplicate branch
                #print("Found an instance at a higher level which is now being moved to be a branch on the managed: ", value)
            #    duplicateBranchTuple = tuple([newpolyObj.className, ids, tuple(valuePath)])
            #    self.replaceOriginalTuple(self, originalPath=valuePath, newPath=[selfTuple,duplicateBranchTuple], newTuple=duplicateBranchTuple)
                #Make sure the new branch has the current manager and the base as it's origin branch set on it.
            #    if(self != value.branch):
            #        value.branch = self
            #    if(self != value.manager):
            #        value.manager = self
        #print("Finished setting value of ", name, " to be ", value)
        super(managerObject, self).__setattr__(name, value)

    #Deletes a tree node, deletes all dependent tree nodes with no existing duplicates
    def deleteTreeNode(self, className, nodePolariId, baseDeleteData=None, deleteData=None, instancesDeleted=[], migratedInstances=[], startDelete=True):
        if(startDelete == True):
            instToDelete = self.objectTables[className][nodePolariId]
            instancesDeleted.append(nodePolariId)
            tupToDelete = self.getInstanceTuple(instToDelete)
            deletePath = self.getTuplePathInObjTree(tupToDelete)

            # Handle instances that are in objectTables but not in objectTree
            # This occurs when instances are created without a branch parameter
            if(deletePath == None):
                # Simply remove from objectTables
                del self.objectTables[className][nodePolariId]
                return (instancesDeleted, migratedInstances)

            deleteData = (instToDelete, tupToDelete, deletePath)
            (baseInstToDelete, baseTupToDelete, baseDeletePath) = deleteData
            baseDeleteData = deleteData
        else:
            (baseInstToDelete, baseTupToDelete, baseDeletePath) = baseDeleteData
            (instToDelete, tupToDelete, deletePath) = deleteData
        #Get all duplicates and main nodes branching from current main node.
        pathsList = self.getAllPathsForTupleInObjTree(tupToDelete)
        #remove current main branch node from the list so we don't immediately delete it.
        removeIndex = None
        curIndex = 0
        for somePath in pathsList:
            if(somePath[len(baseDeletePath)-1] == tupToDelete):
                removeIndex = curIndex
                break
            else:
                curIndex += 1
        if(removeIndex != None):
            pathsList.remove(removeIndex)
        else:
            raise ValueError("Something has gone very wrong... trying to delete node but main node cannot be located, it may have been deleted already?")
        #Go through all duplicates and delete them
        for nodePath in pathsList:
            tempPath = nodePath
            tempPath.pop()
            treeBranch = self.getBranchNode(tempPath)
            #Remove the duplicateNode from the treeBranch
            treeBranch.remove(nodePath[len(nodePath)-1])
        #Access the main node
        treeBranch = self.getBranchNode(baseDeletePath)
        #
        duplicates = []
        mainNodes = []
        for subBranchTuple in treeBranch.keys():
            valueType = subBranchTuple[2].__class__.__name__
            if(valueType == "tuple" or valueType=="NoneType"):
                duplicates.append(subBranchTuple)
            else:
                mainNodes.append(subBranchTuple)
        #Go through all duplicate nodes and delete them since we know they
        #should not be migrated.
        for duplicateKey in duplicates:
            treeBranch.remove(duplicateKey)
        #
        baseDeletePathLength = len(baseDeletePath)
        #Go through main nodes and see whether they can be migrated outside of
        #the current sub-tree being deleted.
        #If they can, migrate them.  If not, delete them and their sub-tree.
        for mainKey in mainNodes:
            #Get all paths
            pathsList = self.getAllPathsForTupleInObjTree(mainKey)
            #Compare to see if any paths exist outside of baseDeletePath
            insidePaths = []
            outsidePaths = []
            for somePath in pathsList:
                isOutside = False
                somePathLength = len(somePath)
                if(baseDeletePathLength <= somePathLength):
                    iter = range(0,baseDeletePathLength - 1)
                    for i in iter:
                        if(not somePath[i] == baseDeletePath[i]):
                            isOutside = True
                            break
                    if(isOutside):
                        outsidePaths.append(somePath)
                    else:
                        insidePaths.append(somePath)
                else:
                    #Since it is lower level than delete path, cannot possibly
                    #be under the deleted sub-tree, so we migrate the sub-tree.
                    #Note: Under normal conditions this should never happen because
                    #main nodes should always exist at lowest path length...
                    #will put it here just in case though.
                    outsidePaths.append(somePath)
            #Delete all duplicates on inside paths
            for inPath in insidePaths:
                tempPath = inPath
                tempPath.pop()
                inBranch = self.getBranchNode(tempPath)
                #Remove the duplicateNode from the treeBranch
                inBranch.remove(inPath[len(inPath)-1])
            shortestPath = None
            #If no outside paths exist, the main node and it's sub-tree must be deleted.
            if(len(outsidePaths) == 0):
                newTupToDelete = mainKey
                newInstToDelete = mainKey[2]
                instancesDeleted.append(newInstToDelete)
                newDeletePath = self.getTuplePathInObjTree(newTupToDelete)
                newDeleteData = (newInstToDelete, newTupToDelete, newDeletePath)
                (instancesDeleted, migratedInstances) = self.deleteTreeNode(className=className, nodePolariId=nodePolariId, baseDeleteData=baseDeleteData, deleteData=newDeleteData, instancesDeleted=instancesDeleted, migratedInstances=migratedInstances, startDelete=False)
            #If an outside path exists, find the path with shortest length, and migrate to it.
            else:
                shortestPath = outsidePaths[0]
                shortestPathLength = len(shortestPath)
                for outPath in outsidePaths:
                    if(len(shortestPath) < shortestPathLength):
                        shortestPath = outPath
                        shortestPathLength = len(outPath)
                migratedInstances = self.migrateTreeNode(originalPath=mainKey,newPath=shortestPath,migratedInstances=migratedInstances)
        return (instancesDeleted, migratedInstances)

    #Migration of a tree node should only occur as a part of the deletion process,
    #since the process of deletion can create an irregulariy if not handled.
    #Under normal circumstances all migrations would be simple migrations since
    #they happen when a new node is created at a lower path length than it's
    #current existing main node.
    def migrateTreeNode(self, originalPath, newPath, migratedInstances, removeOriginal=True):
        #Get the branch we want to load the new branch onto
        targetPath = newPath
        targetPath.pop()
        originalParentPath = originalPath
        originalParentPath.pop()
        originalParentInstance = originalParentPath[len(originalParentPath)-1][2]
        originalInstance = originalPath[len(originalPath)-1][2]
        targetBranch = self.getBranchNode(targetPath)
        #Remove the duplicate being replaced
        targetBranch.remove(newPath[len(newPath)-1])
        #Get the original branch that needs to be migrated.
        originalTuple = originalPath[len(originalPath)-1]
        originalBranch = self.getBranchNode(originalPath)
        originalParentBranch = self.getBranchNode(originalParentPath)
        #Check if the branch being migrated to is at an equal or lower depth than
        #the current location, if it is we can directly skip the need for a
        #complex migration process and just move the branch at once.
        if(len(newPath) <= len(originalPath)):
            #Directly move the branch over to the new location.
            targetBranch[originalTuple] = originalBranch
            #Then remove the node from the previous location on original parent branch.
            originalParentBranch.remove(originalTuple)
            if(not removeOriginal):
                #TODO Instead, ensure it is replaced with a duplicate.
                self.getDuplicateInstanceTuple(originalTuple[2])
            else:
                classType = originalTuple[2].__class__.__name__
                self.removeInstanceReferences(instanceWithReferences=originalParentInstance, instanceReferenced=originalInstance)
                #TODO All references to this instance should be removed from the instance
                #that the parent branch references.
            #...
            #Now that it has been successfully migrated and removed from it's
            #original location, we add it to migrated objects and return it.
            migratedInstances.append(originalTuple[2])
        #Now it gets complicated.. first, record what the path shift is.  We will
        #need that to determine what main nodes, if any, will need to move.
        else:
            newPathLength = len(newPath)
            pathShift = len(originalPath) - newPathLength
            mainNodes = []
            for subBranchTuple in originalBranch.keys():
                valueType = subBranchTuple[2].__class__.__name__
                #Ignore duplicates and add all main nodes to a list.
                if(valueType != "tuple" and valueType!="NoneType"):
                    mainNodes.append(subBranchTuple)
            #Go through each main node and compare all of their paths to see if any
            #would be a shorter path than a what simple migration would result in.
            for someNode in mainNodes:
                #Get all paths
                pathsList = self.getAllPathsForTupleInObjTree(someNode)
                #Check to see if any path shorter than the converted path will exist.
                shortestPathLength = newPathLength
                shortestPath = None
                foundShorterPath = False
                for somePath in pathsList:
                    if(len(somePath) < shortestPathLength):
                        shortestPathLength = len(somePath)
                        shortestPath = somePath
                        foundShorterPath = True
                if(foundShorterPath):
                    #TODO migrate to the shorter path and replace with duplicate while leaving references.
                    pass
                else:
                    migratedInstances.append(someNode[2])
                
    #Removes all references to a given instance from a given instance's variables.
    def removeInstanceReferences(self, instanceWithReferences, instanceReferenced):
        #Get polyTyping for instances
        instanceVars = instanceWithReferences.__dict__
        instanceReferencedType = instanceReferenced.__class__.__name__
        instanceReferencedTyping = self.objectTypingDict(instanceReferencedType)
        variablesWithReferences = instanceReferencedTyping.objectReferencesDict[instanceWithReferences.__class__.__name__]
        for someVar in variablesWithReferences:
            if(someVar in instanceVars.keys()):
                varVal = getattr(instanceWithReferences, someVar)
                varType = varVal.__class__.__name__
                if(varType == instanceReferencedType):
                    if(instanceReferenced == varVal):
                        setattr(instanceWithReferences,someVar,None)
                elif(varType == "list" or varType == "polariList"):
                    indexDict = {}
                    index = 0
                    indexCount = 0
                    for elem in varVal:
                        elemType = elem.__class__.__name__
                        if(elemType == instanceReferencedType):
                            if(instanceReferenced == elem):
                                indexDict[indexCount] = index
                    for i in range(0, indexCount):
                        removeIndex = indexDict[i] - i
                        varVal.pop(removeIndex)
                    #After removing all instance matches from the list, we set it.
                    setattr(instanceWithReferences,someVar,varVal)
                        


    #Takes in all information needed to access a class and returns a formatted json string 
    def getJSONforClass(self, absDirPath = os.path.dirname(os.path.realpath(__file__)), definingFile = os.path.realpath(__file__)[os.path.realpath(__file__).rfind('\\') + 1 : os.path.realpath(__file__).rfind('.')], className = 'testClass', passedInstances = None):
        classVarDict = self.getJSONdictForClass(absDirPath=absDirPath,definingFile=definingFile,className=className, passedInstances=passedInstances)
        JSONstring = json.dumps(classVarDict)
        return JSONstring

    def getObjectSourceDetailsANDvalidateInstances(self, passedInstances):
        print("Entered passedInstances validation and details gathering, with passedInstances: ", passedInstances)
        returnDict = {'passedInstances':passedInstances, 'className':None, 'absDirPath':None, 'definingFile':None}
        #print("Initialized returnDict.")
        className = None
        classNames = []
        for someInst in passedInstances:
            if(not someInst.__class__.__name__ in classNames):
                classNames.append(someInst.__class__.__name__)
        #print("Reached end of first loop.")
        if(len(classNames)>=1):
            className = classNames[0]
            returnDict['className'] = className
        elif(len(classNames) == 0):
            return {}
        else:
            errMsg = "In \'getJSONdictForClass\' the parameter passedInstances should contain one or more values and all be of one type, instead had list: " + str(classNames)
            raise ValueError(errMsg)
        #print("Got past valueError, confirming only one class type in list")
        #Go through and find correct polyTyping.
        correctObjectTyping = None
        for somePolyTyping in self.objectTyping:
            if(somePolyTyping.className == className):
                correctObjectTyping = somePolyTyping
                break
        if(correctObjectTyping == None):
            errMsg = "PolyTyping for type " + className + " could not be found!"
            raise ValueError(errMsg)
        print("PolyTyping for object type ", className, " is found on PolyTyping instance ", correctObjectTyping)
        print("The object Typing\'s polariSourceFile is ", correctObjectTyping.polariSourceFile)
        print("The executable object\'s file name is ", correctObjectTyping.polariSourceFile.name)
        print("The executable object\'s path is ", correctObjectTyping.polariSourceFile.Path)
        returnDict['absDirPath'] = correctObjectTyping.polariSourceFile.Path
        returnDict['definingFile'] = correctObjectTyping.polariSourceFile.name
        if(returnDict['absDirPath'] == None):
            raise ValueError("No value found for Path on source file for class "+className)
        elif(returnDict['absDirPath'] == None):
            raise ValueError("No value found for file name on source file for class "+className)
        print("Passing back returnDict.")
        return returnDict


    #Gets all data for a class and returns a Dictionary which is convertable to a json object.
    def getJSONdictForClass(self, passedInstances, varsLimited=[]):
        print("Attempting to call passedInstances validation, passedInstances:", passedInstances, " and varsLimited: ", varsLimited)
        if(type(passedInstances).__name__ == "dict"):
            passedInstances = list(passedInstances.values())
        if(len(passedInstances) > 0):
            objSourceDetailsDict = self.getObjectSourceDetailsANDvalidateInstances(passedInstances=passedInstances)
            #Path to the Directory the file is in.
            absDirPath = objSourceDetailsDict['absDirPath']
            #The name of the file which contains the given class.
            definingFile = objSourceDetailsDict['definingFile']
            #The name of the class being retrieved.
            className = objSourceDetailsDict['className']
        else:
            objSourceDetailsDict = {}
        #
        varsLimited = varsLimited
        print("Successfully extracted details.")
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
                    if(not callable(getattr(someInstance, classElement)) and not classElement in varsLimited):
                        classInstanceDict[classElement] = None
                classVarDict[0]["data"].append( self.getJSONclassInstance(someInstance, classInstanceDict) )
        elif(passedInstances == None):
            pass
            #if(passedInstances == None):
                #classInstance = returnedClassInstantiationMethod()
                #classInfoDict = classInstance.__dict__
        else: #Accounts for the case where only a single instance of the class is passed into the function
            classInstanceDict = {}
            classInfoDict = passedInstances.__dict__
            for classElement in classInfoDict:
                #print('got attribute: ' + classElement)
                if(not callable(getattr(passedInstances, classElement)) and not classElement in varsLimited):
                    classInstanceDict[classElement] = None
                    #print('not callable attribute: ' + classElement)
            classVarDict[0]["data"].append( self.getJSONclassInstance(passedInstances, classInstanceDict) )
        #print('Class Variable Dictionary: ', classVarDict)
        return classVarDict

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
            if(classInstance.__class__.__name__ == 'polyTypedObject' or classInstance.__class__.__name__ == 'polyTypedVariable'):
                print('Trying to create typing for polyTyping when it should already exist.')
            else:
                obj = self.makeDefaultObjectTyping(classInstance=classInstance)
        elif classObj != None:
            if(classObj.__name__ == 'polyTypedObject' or classObj.__name__ == 'polyTypedVariable'):
                print('Trying to create typing for polyTyping when it should already exist.')
            else:
                obj = self.makeDefaultObjectTyping(classObj=classObj)
        return obj

    def getJSONclassInstance(self, passedInstance, classInstanceDict):
        dataTypesPython = ['str','int','float','complex','list','tuple','range','dict','set','frozenset','bool','bytes','bytearray','memoryview', 'NoneType']
        #print("entered getJSONclassInstance()")
        for someVariableKey in classInstanceDict.keys():
            curAttr = getattr(passedInstance, someVariableKey)
            curAttrType = type(curAttr).__name__
            #print("adding elem of type ", curAttrType ," with value: ", curAttr)
            #Handles Cases where particular classes must be converted into a string format.
            if(curAttrType == 'dateTime'):
                classInstanceDict[someVariableKey] = curAttr.strftime()
            elif(curAttrType == 'struct_time'):
                classInstanceDict[someVariableKey] = time.strftime('%Y-%m-%dT%H:%M:%SZ',curAttr)
            elif(curAttrType == 'TextIOWrapper'):
                classInstanceDict[someVariableKey] = curAttr.name
            elif(curAttrType == 'type'):
                classInstanceDict[someVariableKey] = str(curAttr)
            elif(curAttrType == 'bytes' or curAttrType == 'bytearray'):
                #print('found byte var ', someVariableKey, ': ', classInstanceDict[someVariableKey])
                classInstanceDict[someVariableKey] = curAttr.decode()
            elif(curAttrType == 'dict'):
                classInstanceDict[someVariableKey] = self.convertSetTypeIntoJSONdict(curAttr)
            elif(curAttrType == 'tuple' or curAttrType == 'list' or curAttrType == 'polariList'):
                #print('found byte var ', someVariableKey, ': ', classInstanceDict[someVariableKey])
                classInstanceDict[someVariableKey] = self.convertSetTypeIntoJSONdict(curAttr)
            elif(inspect.ismethod(curAttr)):
                #print('found bound method (not adding this) ', someVariableKey, ': ', getattr(passedInstance, someVariableKey))
                errMsg = "Found a class method - " + curAttr + " being set as a key"
                raise ValueError(errMsg)
                classInstanceDict[someVariableKey] = "Method-" + curAttr.__name__
            elif(type(curAttr).__name__ == "App"):
                classInstanceDict[someVariableKey] = "FALCON-API-APP-REFERENCE"
            elif(inspect.isclass(type(curAttr)) and not curAttrType in dataTypesPython):
                #For now just set the value to be the name of the class, will build functionality to put in list of identifiers as a string. Ex: 'ClassName(id0:val0, id1:val1)'
                #print('found custom class or type ', someVariableKey, ': ', getattr(passedInstance, someVariableKey))
                if(not type(curAttr).__name__ in self.objectTypingDict.keys()):
                    raise Exception("invalid type detected : " + type(curAttr).__name__)
                instIds = ["CLASS-" + curAttrType + "-REFERENCE", self.convertSetTypeIntoJSONdict(passedSet=self.getInstanceIdentifiers(curAttr))]
                classInstanceDict[someVariableKey] = instIds
            #Other cases are cleared, so it is either good or it is unaccounted for so we should let it throw an error.
            else:
                #print('Standard type: ', type(getattr(passedInstance, someVariableKey)), getattr(passedInstance, someVariableKey))
                classInstanceDict[someVariableKey] = getattr(passedInstance, someVariableKey)
        return classInstanceDict

    #Converts a passed in list, tuple, or python dictionary into a jsonifiable dictionary where the keys are the datatypes in python
    def convertSetTypeIntoJSONdict(self, passedSet):
        #print("Entered \'convertSetTypeIntoJSONdict\' for value: ", passedSet)
        returnVal = None
        if(type(passedSet).__name__ == 'tuple' or type(passedSet).__name__ == 'list' or type(passedSet).__name__ == 'polariList'):
            returnVal = []
            for elem in passedSet:
                elemType = type(elem).__name__
                #Handles Cases where particular classes must be converted into a string format.
                if(elemType == 'dateTime'):
                    returnVal.append(elem.strftime())
                elif(elemType == 'struct_time'):
                    returnVal.append(time.strftime('%Y-%m-%dT%H:%M:%SZ',elem))
                elif(elemType == 'TextIOWrapper'):
                    returnVal.append(elem.name)
                elif(elemType == 'type'):
                    returnVal.append(str(elem))
                elif(elemType == 'bytes' or elemType == 'bytearray'):
                    #print('found byte var ', someVariableKey, ': ', classInstanceDict[someVariableKey])
                    returnVal.append(elem.decode())
                elif(elemType == 'tuple' or elemType == 'list' or elemType == 'polariList'):
                    returnVal.append(self.convertSetTypeIntoJSONdict(passedSet=elem))
                elif(elemType == 'dict'):
                    returnVal.append(self.convertSetTypeIntoJSONdict(passedSet=elem))
                elif(elemType == "App"):
                    returnVal.append("FALCON-API-APP-REFERENCE")
                elif(inspect.ismethod(elem)):
                    #print('found bound method (not adding this) ', someVariableKey, ': ', getattr(passedInstance, someVariableKey))
                    returnVal.append({"__method__":{"name":elem.__name__,"parameterSignature":inspect.signature(elem),"parameterQuery":[],"execute":False}})
                elif(inspect.isclass(type(elem)) and not elemType in dataTypesPython):
                    #For now just set the value to be the name of the class, will build functionality to put in list of identifiers as a string. Ex: 'ClassName(id0:val0, id1:val1)'
                    #print('found custom class or type ', elemType, ' with value ', elem, 'in passed set ', passedSet)
                    if(not type(elem).__name__ in self.objectTypingDict.keys()):
                        raise Exception("invalid type detected : " + type(elem).__name__)
                    instIds = ["CLASS-" + elemType + "-REFERENCE", self.convertSetTypeIntoJSONdict(passedSet=self.getInstanceIdentifiers(elem))]
                    returnVal.append(instIds)
                #Other cases are cleared, so it is either good or it is unaccounted for so we should let it throw an error.
                else:
                    #print('Standard type: ', type(getattr(passedInstance, someVariableKey)))
                    returnVal.append(elem)
        elif(type(passedSet).__name__ == 'dict'):
            #print("Entered Dict section of parsing...")
            returnVal = {}
            convertedKeyMap = {}
            tupleKeysNumbering = 0
            classKeyNumbering = 0
            #Creates a map of old key values - to - valid key values for json.
            for keyVal in passedSet.keys():
                elemType = type(keyVal).__name__
                #Handles Cases where particular classes must be converted into a string format.
                if(type(keyVal).__name__ == 'dateTime'):
                    convertedKeyMap[keyVal] = keyVal.strftime()
                elif(type(keyVal).__name__ == 'TextIOWrapper'):
                    convertedKeyMap[keyVal] = keyVal.name
                elif(type(keyVal).__name__ == 'TextIOWrapper'):
                    convertedKeyMap[keyVal] = str(keyVal)
                elif(type(keyVal).__name__ == 'bytes' or type(keyVal).__name__ == 'bytearray'):
                    #print('found byte var ', someVariableKey, ': ', classInstanceDict[someVariableKey])
                    convertedKeyMap[keyVal] = keyVal.decode()
                elif(type(keyVal).__name__ == 'tuple'):
                    convertedKeyMap[keyVal] = "TUPLE-KEY-" + str(tupleKeysNumbering)
                    tupleKeysNumbering += 1
                elif(inspect.isclass(type(keyVal)) and not type(keyVal).__name__ in dataTypesPython):
                    #For now just set the value to be the name of the class, will build functionality to put in list of identifiers as a string. Ex: 'ClassName(id0:val0, id1:val1)'
                    #print('found custom class or type ', someVariableKey, ': ', getattr(passedInstance, someVariableKey))
                    convertedKeyMap[keyVal] = "CLASS-KEY-" + type(keyVal).__name__ + "-" + str(classKeyNumbering)
                    classKeyNumbering += 1
                #Other cases are cleared, so it is either good or it is unaccounted for so we should let it throw an error.
                else:
                    #print('Standard type: ', type(getattr(passedInstance, someVariableKey)))
                    convertedKeyMap[keyVal] = keyVal
            for keyVal in passedSet.keys():
                correctedKey = convertedKeyMap[keyVal]
                if("TUPLE-KEY" in convertedKeyMap[keyVal]):
                    returnVal[convertedKeyMap[keyVal]] = self.convertSetTypeIntoJSONdict(passedSet=keyVal)
                    correctedKey = correctedKey + "-VALUE"
                #Handles Cases where particular classes must be converted into a string format.
                if(type(passedSet[keyVal]).__name__ == 'dateTime'):
                    returnVal[correctedKey] = passedSet[keyVal].strftime()
                elif(type(passedSet[keyVal]).__name__ == 'TextIOWrapper'):
                    returnVal[correctedKey] = passedSet[keyVal].name
                elif(type(passedSet[keyVal]).__name__ == 'type'):
                    returnVal[correctedKey] = str(passedSet[keyVal])
                elif(type(passedSet[keyVal]).__name__ == 'bytes' or type(passedSet[keyVal]).__name__ == 'bytearray'):
                    #print('found byte var ', someVariableKey, ': ', classInstanceDict[someVariableKey])
                    returnVal[correctedKey] = passedSet[keyVal].decode()
                elif(type(passedSet[keyVal]).__name__ == 'tuple' or type(passedSet[keyVal]).__name__ == 'list' or type(passedSet[keyVal]).__name__ == 'dict' or type(passedSet[keyVal]).__name__ == 'polariList'):
                    returnVal[correctedKey] = self.convertSetTypeIntoJSONdict(passedSet=keyVal)
                elif(inspect.isclass(type(passedSet[keyVal])) and not type(passedSet[keyVal]).__name__ in dataTypesPython):
                    #For now just set the value to be the name of the class, will build functionality to put in list of identifiers as a string. Ex: 'ClassName(id0:val0, id1:val1)'
                    #print('found custom class or type ', someVariableKey, ': ', getattr(passedInstance, someVariableKey))
                    returnVal[correctedKey] = type(passedSet[keyVal]).__name__
                #Other cases are cleared, so it is either good or it is unaccounted for so we should let it throw an error.
                else:
                    #print('Standard type: ', type(getattr(passedInstance, someVariableKey)))
                    returnVal[keyVal] = keyVal
        else:
            ValueError("Passed invalid value into ")
        returnJSON = [{type(passedSet).__name__:returnVal}]
        return returnJSON

    #
    def getListOfInstancesAtDepth(self, target_depth, depth=0, traversalList=[], source=None):
        #print("In \'getListOfClassInstances\' branch with traveral list : ", traversalList)
        if(source==None):
            source = self
        ids = self.getInstanceIdentifiers(source)
        sourceTuple = tuple([source.__class__.__name__, ids, source])
        instanceList = []
        tempList = []
        if(traversalList != None):
            branch = self.getBranchNode(traversalList = traversalList)
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

    #{"sampleStringAttribute":{"EQUALS":("id-1234","sampleClassName")),"CONTAINS":("","AND","")}, "sampleRefAttribute":{"IN":["polariID-0", ...]}}
    def getListOfInstancesByAttributes(self, className, attributeQueryDict="*"):
        print("Calling query using value: ", attributeQueryDict)
        getListResult = self.getListOfClassInstances(className="PolyTypedVariable")
        print("getListOfClassInstances result : ", getListResult)
        if(not className in self.objectTables.keys()):
            print("Not found in objecttables", className)
            return {}
        allClassInstancesDict = self.objectTables[className]
        print("allClassInstancesDict : ",allClassInstancesDict)
        remainingInstances = allClassInstancesDict
        eliminatedInstances = {}
        if(attributeQueryDict == "*"):
            return allClassInstancesDict
        elif(type(attributeQueryDict).__name__ == "list" or type(attributeQueryDict).__name__ == "polariList"):
            remainingInstances = self.listConditionalRequirementsForQuery(className=className, comboMethod="AND",queryListSegment=attributeQueryDict, remainingInstancesDict=remainingInstances)
        elif(type(attributeQueryDict).__name__ == "dict"):
            remainingInstances = self.dictAttributeRequirementsForQuery(className=className, queryDictSegment=attributeQueryDict, remainingInstancesDict=remainingInstances)
        else:
            raise ValueError("attributeQuery value must be of type list or polariList, or a string containing *, instead it is ", attributeQueryDict)
        return remainingInstances

    #Pass in a query Segment containing a tuple with an AND or OR operator
    #in the middle.
    def listConditionalRequirementsForQuery(self, className, queryListSegment, remainingInstancesDict, comboMethod="AND"):
        if(not comboMethod in ["AND", "OR"]):
            errMsg = "Attempted to generate query utilizing incorrect value '" + comboMethod + "' in the first position of a tuple in a Conditional Requirements List, only the values AND & OR are allowed in those positions for a query."
            raise ValueError(errMsg)
        tempInstancesDict = None
        ListOfRemainingInstanceDictsForUnion = []
        for logicTuple in queryListSegment:
            if(type(logicTuple).__name__ == "tuple"):
                if(len(logicTuple) != 2 and logicTuple[0] in ["AND", "OR"]):
                    #At the base section, we assume it is an AND initially for the given list.
                    segmentType = type(logicTuple[1]).__name__
                    if(segmentType == "dict"):
                        tempInstancesDict = self.dictAttributeRequirementsForQuery(className=className, queryDictSegment=logicTuple[1], remainingInstancesDict=remainingInstancesDict)
                    elif(segmentType == "polariList" or segmentType == "list"):
                        tempInstancesDict = self.listConditionalRequirementsForQuery(className=className, comboMethod=logicTuple[0],queryListSegment=logicTuple[1], remainingInstancesDict=remainingInstancesDict)
                    else:
                        errMsg = "Found unexpected value '"+ logicTuple[1] +"' of type '"+ segmentType +"' in conditional requirement tuple"
                        raise ValueError(errMsg)
                    if(comboMethod == "AND"):
                        remainingInstancesDict = tempInstancesDict
                    elif(comboMethod == "OR"):
                        ListOfRemainingInstanceDictsForUnion.append(tempInstancesDict)
        #Returns using this method when OR Conditional is being applied.
        if(comboMethod == "OR"):
            unionedInstancesDict = {}
            for partialInstancesDict in ListOfRemainingInstanceDictsForUnion:
                for someId in partialInstancesDict.keys():
                    if(not someId in unionedInstancesDict):
                        unionedInstancesDict[someId] = partialInstancesDict[someId]
            return unionedInstancesDict
        #Return using this method when AND Conditional is being applied
        else:
            return remainingInstancesDict



    def dictAttributeRequirementsForQuery(self, className, queryDictSegment, remainingInstancesDict):
        print("Starting query execution using atributeQueryDict: ", queryDictSegment)
        attributeQueryDict = queryDictSegment
        remainingInstances = remainingInstancesDict
        eliminatedInstances = {}
        for someAttribute in attributeQueryDict:
            if("EQUALS" in attributeQueryDict[someAttribute]):
                querySegment = attributeQueryDict[someAttribute]["EQUALS"]
                querySegmentTyping = type(querySegment).__name__
                #print("Entered EQUALS section of Query.  QuerySegment is type ",querySegmentTyping," and has value: ", querySegment)
                if(querySegmentTyping == "str"):
                    #print("In str section")
                    #Scenario where it is expected for attribute of instance
                    #to be an exact instance of a type with an exact id value.
                    if(someAttribute == "id"):
                        #print("in id section")
                        if(querySegment in self.objectTables[className].keys()):
                            #print("querySegment found in objectTables")
                            #Find objects with the given attribute equal
                            for remainingInstanceId in remainingInstances.keys():
                            #    print("remaining Id: ", remainingInstanceId)
                                remainingInstanceMeetsCriteria = False
                                if(remainingInstanceId == querySegment):
                                    returnDict = {remainingInstanceId:self.objectTables[className][remainingInstanceId]}
                                    #print("ReturnDict = ", returnDict)
                                    return returnDict
                            #remainingInstanceMeetsCriteria = False
                            #remainingInstance = self.objectTables[querySegment][remainingInstanceId]
                            #if(hasattr(remainingInstance, someAttribute)):
                            #    referencedInstance = getattr(remainingInstance, someAttribute)
                            #    if(hasattr(referencedInstance, 'id')):
                            #        if(referencedInstance.Id == querySegment):
                            #            remainingInstanceMeetsCriteria = True
                                if(not remainingInstanceMeetsCriteria):
                                    #add to eliminated instances
                                    eliminatedInstances[querySegment] = self.objectTables[className][remainingInstanceId]
                    else:
                        for remainingInstanceId in remainingInstances.keys():
                            remainingInstanceMeetsCriteria = False
                            if(remainingInstanceId != querySegment):
                                remainingInstanceMeetsCriteria = True
                        print("finding instances with non-id attribute of type string.")
                else:
                    raise ValueError("Entered invalid type into EQUALS section of query.")
            #Remove eliminated instances from the remaining instances dict.
            if(len(eliminatedInstances) != 0):
                for someInstId in eliminatedInstances.keys():
                    remainingInstances.pop(someInstId)
                eliminatedInstances = []
            #
            if("CONTAINS" in attributeQueryDict[someAttribute]):
                print("Entered 'contains' segment of query.")
                querySegment = attributeQueryDict[someAttribute]["CONTAINS"]
                querySegmentTyping = type(querySegment).__name__
                if(querySegmentTyping == "str"):
                    print("In string section of CONTAINS")
                    #Find objects with the given attribute equal
                    for remainingInstanceId in remainingInstances.keys():
                        print("Analyzing for Id ", remainingInstanceId)
                        remainingInstanceMeetsCriteria = False
                        remainingInstance = self.objectTables[className][remainingInstanceId]
                        if(hasattr(remainingInstance, someAttribute)):
                            print("Found attribute in instance with CONTAINS: ", someAttribute, " with value: ", getattr(remainingInstance, someAttribute))
                            if(querySegment in getattr(remainingInstance, someAttribute)):
                                remainingInstanceMeetsCriteria = True
                        if(not remainingInstanceMeetsCriteria):
                            #add to eliminated instances
                            eliminatedInstances[remainingInstanceId] = remainingInstance
            #Remove eliminated instances from the remaining instances dict.
            if(len(eliminatedInstances) != 0):
                for someInstId in eliminatedInstances.keys():
                    remainingInstances.pop(someInstId)
                eliminatedInstances = []
            if("IN" in attributeQueryDict[someAttribute]):
                print("Entered 'IN' segment of query.")
                querySegment = attributeQueryDict[someAttribute]["IN"]
                querySegmentTyping = type(querySegment).__name__
                print("querySegment type is ", querySegmentTyping, " and it's value is ", querySegment)
                foundMatch = False
                if(querySegmentTyping == "list"):
                    for remainingInstanceId in remainingInstances.keys():
                        remainingInstanceMeetsCriteria = False
                        remainingInstance = self.objectTables[className][remainingInstanceId]
                        if not remainingInstanceId in querySegment:
                            eliminatedInstances[remainingInstanceId] = remainingInstance
                            print("Eliminating instances using dict: ", eliminatedInstances)
                            #Queue Id to be removed from remaining Ids.
                        else:
                            print("Found id", remainingInstanceId," in querySegment")
                #Remove eliminated instances from the remaining instances dict.
                if(len(eliminatedInstances.keys()) != 0):
                    for someInstId in eliminatedInstances.keys():
                        remainingInstances.pop(someInstId)
                    eliminatedInstances = []
        print("remainingInstancesDict = ", remainingInstances)
        return remainingInstances


    #
    def getListOfClassInstances(self, className, traversalList=[], source=None):
        if(source==None):
            source = self
        #else:
        #    return source.getListOfClassInstances(className=className, traversalList=traversalList, source=source)
        ids = self.getInstanceIdentifiers(source)
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
                    if(branchTuple[0] == className and branchTuple[2].__class__.__name__ != "tuple"):
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
            filePath = os.path.dirname(classDefiningFile)
            pass
        except:
            print('Caught exception for retrieving file, thereby instance of type', classInstance.__class__.__name__ , ' with a value of ', classInstance,' must be a built-in class')
            isBuiltinClass = True
            pass
        if(isBuiltinClass):
            sourceFiles = []
        else:
            dotIndex = classDefiningFile.index(".")
            #Get final index of forward or backslash, if neither then set index to zero
            lastSlashIndex = classDefiningFile.rfind("/")
            if(lastSlashIndex == -1):
                lastSlashIndex = classDefiningFile.rfind("\\")
            if(lastSlashIndex == -1):
                lastSlashIndex = 0
            classDefiningFile = classDefiningFile[0:dotIndex]
            fileName = classDefiningFile[lastSlashIndex+1:dotIndex]
            filePath = classDefiningFile[0:lastSlashIndex]
            pythonSourceFile = self.makeFile(name=fileName, extension='py', Path=filePath)
            sourceFiles = [pythonSourceFile]
            #print('Class file name: ', fileName)
        if(classInstance != None):
            classDefaultTyping = polyTypedObject(manager=self, sourceFiles=sourceFiles, className=classInstance.__class__.__name__, identifierVariables=['id'], sampleInstances=[classInstance])
            #return classDefaultTyping
        elif(classObj != None):
            classDefaultTyping = polyTypedObject(manager=self, sourceFiles=sourceFiles, className=classObj.__name__, identifierVariables=['id'], classDefinition=classObj)
            #return classDefaultTyping
        if(classInstance != None):
            if(classInstance.__class__.__name__ != 'list' and classInstance.__class__.__name__ != 'polariList'):
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
        if(instance.__class__.__name__ == 'treeObject' or instance.__class__.__name__ == 'managerObject'):
            isValid = True
        else:
            for parentObj in instance.__class__.__bases__:
                #print("Iterated Parent object in getInstanceIdentifiers: ", parentObj.__name__)
                if(parentObj.__name__ == "treeObject" or parentObj.__name__ == "managerObject" or parentObj.__name__ == "managedFile"):
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
        #print('Path passed in value: ', traversalList)
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
                    #if(branchTuple[2] != [] and branchTuple[2] != None):
                    #    print("Returning non-empty path! - ", branchTuple[2])
                    return branchTuple[2]
                #Case of an exact match.
                elif(branchTuple[2] == instanceTuple[2]):
                    #print("Found an exact match in the tree for instance: ", instanceTuple[2])
                    #if(traversalList != [] and traversalList != None):
                    #    print("Returning non-empty path! - ", traversalList)
                    traversalList = traversalList + [branchTuple]
                    return traversalList
                #print('Found tuple match!')
                #print(traversalList)
                #return traversalList
        for branchTuple in branch.keys():
            path = self.getTuplePathInObjTree(traversalList=traversalList+[branchTuple],instanceTuple=instanceTuple)
            if(path != None):
                #if(path != [] and path != None):
                #    print("Returning non-empty path! - ", path)
                return path
        #if(traversalList == []):
        #    print('Tuple not found in tree!')
        #    print(instanceTuple)
        #if(path != [] and path != None):
        #    print("Returning non-empty path! - ", path)
        return path

    #Will go through every dictionary in the object tree and return branching depth of the tuple
    #if the tuple exists within the tree.
    def getAllPathsForTupleInObjTree(self, instanceTuple, traversalList=[], allPaths=[]):
        branch = self.getBranchNode(traversalList = traversalList)
        #Handles the case where no further branches exist, meaning, it is currently on a duplicate Node.
        if(branch == None):
            return allPaths
        #print('Branch to be searched: ', branch)
        for branchTuple in branch.keys():
            if branchTuple[0] == instanceTuple[0] and branchTuple[1] == instanceTuple[1]:
                allPaths.append(traversalList + [branchTuple])
        for branchTuple in branch.keys():
            allPaths = self.getAllPathsForTupleInObjTree(traversalList=traversalList+[branchTuple],instanceTuple=instanceTuple, allPaths=allPaths)
        #if(traversalList == []):
        #    print('Tuple not found in tree!')
        #    print(instanceTuple)
        #if(path != [] and path != None):
        #    print("Returning non-empty path! - ", path)
        return allPaths

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
                    if( (type(value) == list or type(value).__name__ == "polariList") and not (value == None or value == [])):
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
        #if(len(traversalList) > 2):
        #    print("Trying to add new branch using traversalList of depth 3!! -> ", traversalList)
        #else:
            #print("Encountered instance being added", instance, " which is missing an id.") 
        if(instance != None):
            branchTuple = self.getInstanceTuple(instance)
        elif(branchTuple != None):
            instance = branchTuple[2]
        if(instance == None):
            print("Instance passed was none")
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
        if(hasattr(instance, 'id') and hasattr(self, "objectTables")):
            if(instance.id != None):
                key = instance.__class__.__name__
                if(key in self.objectTables):
                    self.objectTables[key][instance.id] = instance
                else:
                    self.objectTables[key] = {}
                    self.objectTables[key][instance.id] = instance
            else:
                instance.makeUniqueIdentifier()
                print("New instance id: ", instance.id)
                print("Adding Instance to tree but it has an id with value None.")
        if(hasattr(instance, "branch") and branchingInstance != None):
            if(instance.branch == traversalList[len(traversalList) - 1]):
                pass
            elif(instance.branch == None):
                instance.branch = traversalList[len(traversalList) - 1]
        if(traversalList[len(traversalList) - 1] != branchTuple):
            newTraversalList = traversalList + [branchTuple]
        if(traversalList == []):
            #if(type(instance).__name__ == "treeBranchObject"):
            #    print("Attching treeBranchObject at base of tree?")
            self.objectTree[branchTuple] = {}
        elif(branchNode.get(branchTuple) == None):
            #print("Adding new node in addNewBranch on sub-path's tuple: ", traversalList[len(traversalList) - 1])
            branchNode[branchTuple] = {}

    #Accesses a branch node and adds an empty duplicate sub-branch, which contain identifiers and
    #the path to it's actual branch in the third element of it's tuple.
    def addDuplicateBranch(self, traversalList, branchTuple):
        branchNode = self.getBranchNode(traversalList)
        if(branchNode.get(branchTuple) == None):
            branchNode[branchTuple] = None

    #Places a duplicate tuple in the node's original location and re-locates the
    #main node which branches.
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
        mainDirPath = os.getcwd()
        if(mainDirPath.rfind("\\")):
            fileSlash = "\\"
        elif(mainDirPath.rfind("/")):
            fileSlash = "/"
        source_Polari = self.makeFile(name='definePolari', extension='py', Path=mainDirPath + fileSlash + "polariAI")
        source_dataStream = self.makeFile(name='dataStreams', extension='py', Path=mainDirPath + fileSlash + "polariApiServer")
        source_remoteEvent = self.makeFile(name='remoteEvents', extension='py', Path=mainDirPath + fileSlash + "polariApiServer")
        source_managedUserInterface = self.makeFile(name='managedUserInterface', extension='py', Path=mainDirPath + fileSlash + "polariFrontendManagement")
        source_managedFile = self.makeFile(name='managedFiles', extension='py', Path=mainDirPath + fileSlash + "polariFiles")
        source_polariUser = self.makeFile(name='polariUser', extension='py', Path=mainDirPath + fileSlash + "accessControl")
        source_polariUserGroups = self.makeFile(name='polariUserGroup', extension='py', Path=mainDirPath + fileSlash + "accessControl")
        #managedApp and browserSourcePage share the same source file.
        source_managedAppANDbrowserSourcePage = self.makeFile(name='managedApp', extension='py', Path=mainDirPath + fileSlash + "polariFrontendManagement")
        source_managedDatabase = self.makeFile(name='managedDB', extension='py', Path=mainDirPath + fileSlash + "polariDBmanagement")
        source_dataChannel = self.makeFile(name='dataChannels', extension='py', Path=mainDirPath + fileSlash + "polariFiles")
        source_managedExecutable = self.makeFile(name='managedExecutables', extension='py', Path=mainDirPath + fileSlash + "polariFiles")
        source_polariServer = self.makeFile(name='polariServer', extension='py', Path=mainDirPath + fileSlash + "polariApiServer")
        #polyTyped Object and variable are both defined in the same source file
        source_polyTypedObject = self.makeFile(name='polyTyping', extension='py', Path=mainDirPath + fileSlash + "polariDataTyping")
        source_polyTypedVars = self.makeFile(name='polyTypedVars', extension='py', Path=mainDirPath + fileSlash + "polariDataTyping")
        source_polariCRUDE = self.makeFile(name='polariCRUDE', extension='py', Path=mainDirPath + fileSlash + "polariApiServer")
        source_polariAPI = self.makeFile(name='polariAPI', extension='py', Path=mainDirPath + fileSlash + "polariApiServer")
        self_fileInst = inspect.getfile(self.__class__)
        self_completepath = os.path.abspath(self_fileInst)
        self_fileName = self_completepath[self_completepath.rfind('\\')+1:self_completepath.rfind('.')]
        self_path = self_completepath[0:self_completepath.rfind('\\')]
        source_self = self.makeFile(name=self_fileName, extension='py', Path=self_path)
        #print("source complete path: ", self_completepath)
        #print("source_self file name = ", self_fileName)
        #print("source_self file path = ", self_path)
        self.objectTyping = [
            polyTypedObject(sourceFiles=[source_self], className=type(self).__name__, identifierVariables = identifierVariables, objectReferencesDict={}, manager=self),
            polyTypedObject(sourceFiles=[source_polyTypedVars], className='polyTypedVariable', identifierVariables = ['name','polyTypedObj'], objectReferencesDict={'polyTypedObject':['polyTypedVars']}, manager=self, baseAccessDict={"R":{"polyTypedVariable":"*"}}, basePermDict={"R":{"polyTypedVariable":"*"}}, kwRequiredParams=[], kwDefaultParams=[]),
            polyTypedObject(sourceFiles=[source_Polari], className='Polari', identifierVariables = ['id'], objectReferencesDict={}, manager=self, kwRequiredParams=[], kwDefaultParams=[]),
            polyTypedObject(sourceFiles=[source_dataStream], className='dataStream', identifierVariables = ['id'], objectReferencesDict={'managedApp':['dataStreamsToProcess','dataStreamsRequested','dataStreamsAwaitingResponse']}, manager=self, kwRequiredParams=["source"], kwDefaultParams=["channels", "sinkInstances", "recurring"]),
            polyTypedObject(sourceFiles=[source_remoteEvent], className='remoteEvent', identifierVariables = ['id'], objectReferencesDict={'managedApp':['eventsToProcess','eventsToSend','eventsAwaitingResponse']}, manager=self, kwRequiredParams=[], kwDefaultParams=["eventName", "source", "sink", "channels"]),
            polyTypedObject(sourceFiles=[source_managedUserInterface], className='managedUserInterface', identifierVariables = ['id'], objectReferencesDict={'managedApp':['UIs']}, manager=self, kwRequiredParams=[], kwDefaultParams=["hostApp", "launchMethod"]),
            polyTypedObject(sourceFiles=[source_managedFile], className='managedFile', identifierVariables = ['name','extension','Path'], objectReferencesDict={'managedApp':['AppFiles']}, manager=self, kwRequiredParams=[], kwDefaultParams=["name", "Path", "extension"]),
            polyTypedObject(sourceFiles=[source_managedAppANDbrowserSourcePage], className='managedApp', identifierVariables = ['name'], objectReferencesDict={'managedApp':['subApps']}, manager=self, kwRequiredParams=[], kwDefaultParams=["name", "displayName", "Path", "manager"]),
            polyTypedObject(sourceFiles=[source_managedAppANDbrowserSourcePage], className='browserSourcePage', identifierVariables = ['name','Path'], objectReferencesDict={'managedApp':['landingSourcePage','sourcePages']}, manager=self, kwRequiredParams=[], kwDefaultParams=[ "name", "sourceHTMLfile", "supportFiles", "supportPages"]),
            polyTypedObject(sourceFiles=[source_managedDatabase], className='managedDatabase', identifierVariables = ['name','Path'], objectReferencesDict={'managedApp':['DB']}, manager=self, kwRequiredParams=[], kwDefaultParams=[ "name", "manager", "DBurl", "DBtype", "tables", "inRAM"]),
            polyTypedObject(sourceFiles=[source_dataChannel], className='dataChannel', identifierVariables = ['name','Path'], objectReferencesDict={'polariServer':['serverChannel'],'managedApp':['serverChannel','localAppChannel']}, manager=self, kwRequiredParams=["manager"], kwDefaultParams=[ "name", "Path"]),
            polyTypedObject(sourceFiles=[source_managedExecutable], className='managedExecutable', identifierVariables = ['name', 'extension','Path'], objectReferencesDict={}, manager=self, kwRequiredParams=[], kwDefaultParams=["name", "extension", "Path", "manager"]),
            polyTypedObject(sourceFiles=[source_polyTypedObject], className='polyTypedObject', identifierVariables = ['className'], objectReferencesDict={self.__class__.__name__:['objectTyping'],'polyTypedVariable': ['polyTypedVars']}, manager=self, baseAccessDict={"R":{"polyTypedObject":"*"}}, basePermDict={"R":{"polyTypedObject":"*"}}, kwRequiredParams=["className", "manager"], kwDefaultParams=["objectReferencesDict","sourceFiles","identifierVariables", "variableNameList", "baseAccessDict", "basePermDict", "classDefinition", "sampleInstances", "kwRequiredParams", "kwDefaultParams"]),
            polyTypedObject(sourceFiles=[source_polariServer], className='polariServer', identifierVariables = ['name', 'id'], objectReferencesDict={}, manager=self, baseAccessDict={"R":{"polariServer":"*"}}, basePermDict={"R":{"polariServer":"*"}}, kwRequiredParams=[], kwDefaultParams=[ "name", "displayName", "hostSystem", "serverChannel", "serverDataStream"]),
            polyTypedObject(sourceFiles=[source_polariUser], className='User', identifierVariables = ['id'], objectReferencesDict={self.__class__.__name__:['usersList']}, manager=self, baseAccessDict={"R":{"User":"*"}}, basePermDict={"R":{"User":"*"}}, kwRequiredParams=[], kwDefaultParams=[ "username", "password", "unregistered"]),
            polyTypedObject(sourceFiles=[source_polariUserGroups], className='UserGroup', identifierVariables = ['id'], objectReferencesDict={self.__class__.__name__:['userGroupsList']}, manager=self, baseAccessDict={"R":{"UserGroup":"*"}}, basePermDict={"R":{"UserGroup":"*"}}, kwRequiredParams=["name"], kwDefaultParams=["assignedUsers", "userMembersQuery", "permissionSets"]),
            polyTypedObject(sourceFiles=[source_polariAPI], className='polariAPI', identifierVariables = ['id'], objectReferencesDict={"polariServer":['']}, manager=self, baseAccessDict={"R":{"polariAPI":"*"}}, basePermDict={"R":{"polariAPI":"*"}}, kwRequiredParams=["apiName", "polServer"], kwDefaultParams=["minAccessDict", "maxAccessDict", "minPermissionsDict", "maxPermissionsDict",  "eventAPI", "eventObject", "event"]),
            polyTypedObject(sourceFiles=[source_polariCRUDE], className='polariCRUDE', identifierVariables = ['id'], objectReferencesDict={"polariServer":['crudeObjectsList']}, manager=self, baseAccessDict={"R":{"polariCRUDE":"*"}}, basePermDict={"R":{"polariCRUDE":"*"}}, kwRequiredParams=["apiObject", "polServer"], kwDefaultParams=[])
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
            newFile = managedFile(name=name, extension=extension, Path = Path, manager=self)
        elif extension in picExtensions:
            newFile = managedImage(name=name, extension=extension, Path = Path, manager=self)
        elif extension in dataBaseExtensions:
            newFile = managedDatabase(name=name, Path = Path, manager=self)
        elif extension in dataCommsExtensions:
            newFile = dataChannel(name=name, Path = Path, manager=self)
        elif extension in executableExtensions:
            newFile = managedExecutable(name=name, extension=extension, Path = Path, manager=self)
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
    #"[SELECT * FROM testObj WITH { id:(max), testVar:(=None), name:(a%c%), objList:( contains[ secondTestObj WITH { name:(='name') } ] ) } WHERE hasChildren:[ secondTestObj ]")
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