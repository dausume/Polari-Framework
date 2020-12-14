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
        #print('self: ', self)
        #print('args: ', args)
        #print('keywordargs: ', keywordargs)
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
            #print(self.idList)
            #print('Assigning idList to ', self, '.')
        if not 'cloudIdList' in keywordargs.keys():
            setattr(self, 'cloudIdList', [])
        for name in keywordargs.keys():
            #print('In parameters, found attribute ', name, ' with value ', keywordargs[name])
            if(name=='manager' or name=='id' or name=='objectTree' or name=='managedFiles' or name=='id' or name=='db' or name=='idList' or name=='cloudIdList' or name == 'subManagers' or name == 'polServer'):
                setattr(self, name, keywordargs[name])
        self.primePolyTyping()
        #new_init = init(self, *args, **keywordargs)
        self.makeObjectTree()
        if(self.id == None):
            self.makeUniqueIdentifier()
        

    def __setattr__(self, name, value):
        #if(name == 'polServer'):
        #    print('Setting polServer attribute on manager to: ', value)
        if(not hasattr(self, 'objectTyping') or not hasattr(self, 'objectTree') or type(value).__name__ in dataTypesPython):
            #print('setting value on objectTyping..')
            if(name == 'polServer'):
                print("objectTyping exists - ", hasattr(self, 'objectTyping'), ', objectTree exists - ', hasattr(self, 'objectTree'), ', type name - ', type(value).__name__, ' is in dataTypesPython', type(value).__name__ in dataTypesPython)
                #print('Setting polServer attribute on manager to: ', value)
            super(managerObject, self).__setattr__(name, value)
            return
        else:
            print('-----------Setting an Object on  variable, ', name, ' with value: ', value)
        #print("-----------------------------Setting a value on the manager------------------------------------")
        #print('The value being set is: ', value, 'it\'s type is : ', type(value).__name__)
        polyObj = self.getObjectTyping(self.__class__)
        if(name == 'polServer'):
            print('objectTyping for polariServer found: , ', polyObj)
        #In polyObj 'polyObj.className' potential references exist for this object.
        #Here, we get each variable that is a reference or a list of references to a
        #particular type of object.
        if name in polyObj.objectReferencesDict:
            if(value == None or value == []):
                pass
            elif(type(value) == list):
                #Adding a list of objects
                for inst in value:
                    print('Adding one object as element in a list variable, ', name ,' to the manager with value: ', inst)
                    #if(self.identifiersComplete(inst)):
                    ids = self.getInstanceIdentifiers(inst)
                    instPath = self.getTuplePathInObjTree(instanceTuple=tuple([polyObj.className, ids, inst]))
                    if instPath == []:
                        print("found an instance already in the objectTree at the correct location:", inst)
                        pass
                    elif instPath == None:
                        print("found an instance with no existing branch, now creating branch on manager: ", inst)
                        newBranch = tuple([polyObj.className, ids, inst])
                        self.addNewBranch(traversalList=[], branchTuple=newBranch)
                    else:
                        print("Found an instance at a higher level which is now being moved to be a branch on the managed: ", inst)
                        duplicateBranchTuple = tuple([polyObj.className, ids, tuple([])]) 
                        self.replaceOriginalTuple(self, originalPath = instPath, newPath=[duplicateBranchTuple], newTuple=duplicateBranchTuple)
            else:
                print('Adding one object as variable, ', name ,' to the manager with value: ', value)
                #if(self.identifiersComplete(value)):
                ids = self.getInstanceIdentifiers(value)
                valuePath = self.getTuplePathInObjTree(instanceTuple=tuple([polyObj.className, ids, value]))
                if(valuePath == []):
                    print("found an instance already in the objectTree at the correct location:", value)
                    #Do nothing, because the branch is already accounted for.
                    pass
                elif(valuePath == None):
                    #add the new Branch
                    print("found an instance with no existing branch, now creating branch on manager: ", value)
                    newBranch = tuple([polyObj.className, ids, value])
                    self.addNewBranch(traversalList=[], branchTuple=newBranch)
                else:
                    #add as a duplicate branch
                    print("Found an instance at a higher level which is now being moved to be a branch on the managed: ", value)
                    duplicateBranchTuple = tuple([polyObj.className, ids, tuple(valuePath)])
                    self.replaceOriginalTuple(self, originalPath=valuePath, newPath=[duplicateBranchTuple], newTuple=duplicateBranchTuple)
        else:
            #print('Setting attribute to a value: ', value)
            print('Found object: "', value ,'" being assigned to an undeclared reference variable: ', name, 'On object: ', self)
            newpolyObj = self.getObjectTyping(value.__class__)
            print('Setting attribute using a new polariServer polyTyping: ', newpolyObj, '; and it\'s reference dict: ', newpolyObj.objectReferencesDict)
            managerPolyTyping = self.getObjectTyping(self.__class__)
            managerPolyTyping.addToObjReferenceDict(referencedClassObj=value.__class__, referenceVarName=name)
            print('Object\'s referenceDict after assignment: ', newpolyObj.objectReferencesDict)
            if(type(value) == list):
                #Adding a list of objects
                for inst in value:
                    print('Adding one object as element in a list variable, ', name ,' to the manager with value: ', inst)
                    #if(self.identifiersComplete(inst)):
                    ids = self.getInstanceIdentifiers(inst)
                    instPath = self.getTuplePathInObjTree(instanceTuple=tuple([newpolyObj.className, ids, inst]))
                    if instPath == []:
                        print("found an instance already in the objectTree at the correct location:", inst)
                        pass
                    elif instPath == None:
                        print("found an instance with no existing branch, now creating branch on manager: ", inst)
                        newBranch = tuple([newpolyObj.className, ids, inst])
                        self.addNewBranch(traversalList=[], branchTuple=newBranch)
                    else:
                        print("Found an instance at a higher level which is now being moved to be a branch on the managed: ", inst)
                        duplicateBranchTuple = tuple([newpolyObj.className, ids, tuple([])]) 
                        self.replaceOriginalTuple(self, originalPath = instPath, newPath=[duplicateBranchTuple], newTuple=duplicateBranchTuple)
            else:
                print('Adding one object as variable, ', name ,' to the manager with value: ', value)
                #if(self.identifiersComplete(value)):
                ids = self.getInstanceIdentifiers(value)
                valuePath = self.getTuplePathInObjTree(instanceTuple=tuple([newpolyObj.className, ids, value]))
                if(valuePath == []):
                    print("found an instance already in the objectTree at the correct location:", value)
                    #Do nothing, because the branch is already accounted for.
                    pass
                elif(valuePath == None):
                    #add the new Branch
                    print("found an instance with no existing branch, now creating branch on manager: ", value)
                    newBranch = tuple([newpolyObj.className, ids, value])
                    self.addNewBranch(traversalList=[], branchTuple=newBranch)
                else:
                    #add as a duplicate branch
                    print("Found an instance at a higher level which is now being moved to be a branch on the managed: ", value)
                    duplicateBranchTuple = tuple([newpolyObj.className, ids, tuple(valuePath)])
                    self.replaceOriginalTuple(self, originalPath=valuePath, newPath=[duplicateBranchTuple], newTuple=duplicateBranchTuple)
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
            obj = self.makeDefaultObjectTyping(classInstance=classInstance)
        elif classObj != None:
            obj = self.makeDefaultObjectTyping(classObj=classObj)
        return obj

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
        if(source==None and source != self):
            source = self
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
            #Handles the case for when we are on a duplicate branch.
            if(branch == None):
                instanceList = []
            else:
                for branchTuple in branch.keys():
                    if(type(branchTuple[0]) == className and type(branchTuple[2]).__name__ == className):
                        print("Found a match for the class ", className, " in the manager object ", self, ", the matched object was ", branchTuple[2])
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
            print('Caught exception for retrieving file, thereby,', classInstance.__class__.__name__ ,' must be a built-in class')
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
        elif(classObj != None):
            classDefaultTyping = polyTypedObject(manager=self, sourceFiles=sourceFiles, className=classObj.__name__, identifierVariables=['id'])
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
        obj = self.getObjectTyping(classInstance=instance)
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
            branch = branch[tup]
        #print('Branch Found: ', branch)
        return branch

    def getInstanceTuple(self, instance):
            return tuple([type(instance).__name__, self.getInstanceIdentifiers(instance), instance])

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
                if(type(branchTuple[2]) == tuple):
                    #print('Found tuple match!')
                    return branchTuple[2]
                #print('Found tuple match!')
                #print(traversalList)
                return traversalList
        for branchTuple in branch.keys():
            path = self.getTuplePathInObjTree(traversalList=traversalList+[branchTuple],instanceTuple=instanceTuple)
            if(path != None):
                return path
        #if(traversalList == []):
        #    print('Tuple not found in tree!')
        #    print(instanceTuple)
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
                        print('trying to get value ', varName, ' from an instance ', curTuple[2], ' in polyObj ', polyObj.className)
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
    def addNewBranch(self, traversalList, branchTuple):
        branchNode = self.getBranchNode(traversalList)
        if(branchNode.get(branchTuple) == None):
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
        #polyTyped Object and variable are both defined in the same source file
        source_polyTypedObjectANDvariables = self.makeFile(name='polyTypedObject', extension='py')
        self.objectTyping = [
            polyTypedObject(sourceFiles=[source_Polari], className='Polari', identifierVariables = ['id'], objectReferencesDict={'managedApp':['manager'],'polyTypedObject':['manager']}, manager=self),
            polyTypedObject(sourceFiles=[source_dataStream], className='dataStream', identifierVariables = ['id'], objectReferencesDict={'managedApp':['dataStreamsToProcess','dataStreamsRequested','dataStreamsAwaitingResponse']}, manager=self),
            polyTypedObject(sourceFiles=[source_remoteEvent], className='remoteEvent', identifierVariables = ['id'], objectReferencesDict={'managedApp':['eventsToProcess','eventsToSend','eventsAwaitingResponse']}, manager=self),
            polyTypedObject(sourceFiles=[source_managedUserInterface], className='managedUserInterface', identifierVariables = ['id'], objectReferencesDict={'managedApp':['UIs']}, manager=self),
            polyTypedObject(sourceFiles=[source_managedFile], className='managedFile', identifierVariables = ['name','extension','Path'], objectReferencesDict={'managedApp':['AppFiles']}, manager=self),
            polyTypedObject(sourceFiles=[source_managedAppANDbrowserSourcePage], className='managedApp', identifierVariables = ['name'], objectReferencesDict={'managedApp':['subApps','manager'],'polyTypedObject':['manager']}, manager=self),
            polyTypedObject(sourceFiles=[source_managedAppANDbrowserSourcePage], className='browserSourcePage', identifierVariables = ['name','Path'], objectReferencesDict={'managedApp':['landingSourcePage','sourcePages']}, manager=self),
            polyTypedObject(sourceFiles=[source_managedDatabase], className='managedDatabase', identifierVariables = ['name','Path'], objectReferencesDict={'managedApp':['DB']}, manager=self),
            polyTypedObject(sourceFiles=[source_dataChannel], className='dataChannel', identifierVariables = ['name','Path'], objectReferencesDict={'managedApp':['serverChannel','localAppChannel'],'managedSourcePage':['']}, manager=self),
            polyTypedObject(sourceFiles=[source_managedExecutable], className='managedExecutable', identifierVariables = ['name', 'extension','Path'], objectReferencesDict={}, manager=self),
            polyTypedObject(sourceFiles=[source_polyTypedObjectANDvariables], className='polyTypedObject', identifierVariables = ['className'], objectReferencesDict={self.__class__.__name__:['objectTyping'], 'polyTypedVariable':['polyTypedObj']}, manager=self),
            polyTypedObject(sourceFiles=[source_polyTypedObjectANDvariables], className='polyTypedVariable', identifierVariables = ['name','polyTypedObj'], objectReferencesDict={'polyTypedObject':['polyTypedVars']}, manager=self)
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
            source_self = self.makeFile(name=self.__module__, extension='py')
            self.addObjTyping(sourceFiles=[source_self], className=type(self).__name__, identifierVariables=identifierVariables, objectReferencesDict={})
            self.makeDefaultObjectTyping(objTyp)

    def addObjTyping(self, sourceFiles, className, identifierVariables, objectReferencesDict={}):
        foundObj = False
        for objTyp in self.objectTyping:
            if(objTyp.className == className):
                foundObj = True
        if(not foundObj):
            newTypingObj = polyTypedObject(sourceFiles=sourceFiles, className=className, identifierVariables=identifierVariables, objectReferencesDict=objectReferencesDict, manager=self)
        

    def makeFile(self, name=None, extension=None):
        #print('Entered makefile function')
        if extension in fileExtensions:
            newFile = managedFile(name=name, extension=extension)
        elif extension in picExtensions:
            newFile = managedImage(name=name, extension=extension)
        elif extension in dataBaseExtensions:
            newFile = managedDatabase(name=name)
        elif extension in dataCommsExtensions:
            newFile = dataChannel(name=name)
        elif extension in executableExtensions:
            newFile = managedExecutable(name=name, extension=extension)
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