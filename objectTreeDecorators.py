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
from managedImages import *
from dataChannels import *
import types, inspect, base64

#Defines a Decorator @managerObject, which allocates all variables and functions necessary for
#an object to be a the manager object to an Object Tree.
def managerObject(init):
    parameters = inspect.getfullargspec(init)[0]

    @wraps(init)
    def new_init(self, *args):
        #Adding on the necessary variables for a manager object, in the case they are not defined.
        if not 'objectTyping' in zip(parameters[1:], args):
            setattr(self, 'objectTyping', [])
        if not 'manager' in zip(parameters[1:], args):
            setattr(self, 'manager', None)
        if not 'objectTree' in zip(parameters[1:], args):
            setattr(self, 'objectTree', None)
        if not 'managedFiles' in zip(parameters[1:], args):
            setattr(self, 'managedFiles', [])
        for name, value in zip(parameters[1:], args):
            if(name == 'objectTyping' or name=='manager' or name=='objectTree'):
                setattr(self, name, value)
        #Adding on all of the functions and overrides needed for acting as a manager object.
        setattr( self, '__setattr__', types.MethodType(__setattr__, self) )
        setattr( self, 'getObject', types.MethodType(getObject, self) )
        setattr( self, 'getInstanceIdentifiers', types.MethodType(getInstanceIdentifiers, self) )
        setattr( self, 'getDuplicateInstanceTuple', types.MethodType(getDuplicateInstanceTuple, self) )
        setattr( self, 'getInstanceTuple', types.MethodType(getInstanceTuple, self) )
        setattr( self, 'getTuplePathInObjTree', types.MethodType(getTuplePathInObjTree, self) )
        setattr( self, 'makeObjectTree', types.MethodType(makeObjectTree, self) )
        setattr( self, 'addNewBranch', types.MethodType(addNewBranch, self) )
        setattr( self, 'addDuplicateBranch', types.MethodType(addDuplicateBranch, self) )
        setattr( self, 'replaceOriginalTuple', types.MethodType(replaceOriginalTuple, self) )
        setattr( self, 'primePolyTyping', types.MethodType(primePolyTyping, self) )
        setattr( self, 'addObjTyping', types.MethodType(addObjTyping, self) )
        setattr( self, 'makeFile', types.MethodType(makeFile, self) )
        new_init = init(self, *args)
    return new_init

def __setattr__(self, name, value):
        polyObj = self.objectTyping[type(self).__name__]
        #In polyObj 'polyObj.className' potential references exist for this object.
        #Here, we get each variable that is a reference or a list of references to a
        #particular type of object.
        if name in polyObj.objectReferencesDict:
            if(value == None or value == []):
                pass
            elif(type(value) == list):
                #Adding a list of objects
                for inst in value:
                    ids = self.getInstanceIdentifiers(inst)
                    instPath = self.getTuplePathInObjTree(instanceTuple=tuple([polyObj.className, ids, inst]))
                    if instPath == []:
                        pass
                    elif instPath == None:
                        newBranch = tuple([polyObj.className, ids, inst])
                        self.addNewBranch(traversalList=[], branchTuple=newBranch)
                    else:
                        #add as a duplicate branch
                        duplicateBranchTuple = tuple([polyObj.className, ids, tuple([])]) 
                        self.replaceOriginalTuple(self, originalPath = instPath, newPath=[duplicateBranchTuple], newTuple=duplicateBranchTuple)
            else:
                #Adding one object
                ids = self.getInstanceIdentifiers(value)
                valuePath = self.getTuplePathInObjTree(instanceTuple=tuple([polyObj.className, ids, value]))
                if(valuePath == []):
                    #Do nothing, because the branch is already accounted for.
                    pass
                elif(valuePath == None):
                    #add the new Branch
                    newBranch = tuple([polyObj.className, ids, value])
                    self.addNewBranch(traversalList=[], branchTuple=newBranch)
                else:
                    #add as a duplicate branch
                    duplicateBranchTuple = tuple([polyObj.className, ids, tuple(valuePath)])
                    self.replaceOriginalTuple(self, originalPath=valuePath, newPath=[duplicateBranchTuple], newTuple=duplicateBranchTuple)
        super(setattr, self).__setattr__(name, value)

#Returns another polyTyped Object instance from the manager object
def getObject(self, className):
    for obj in self.objectTyping:
        print(obj.className)
        if(obj.className == className):
            return obj
    return None

def getInstanceIdentifiers(self, instance):
    obj = self.getObject(type(instance).__name__)
    idVars = obj.identifiers
    #Compiles a dictionary of key-value pairs for the identifiers 
    identifiersDict = {}
    for id in idVars:
        identifiersDict[id] = getattr(instance,id)
        listOfIdTuples = identifiersDict.items()
        identifiersTuplified = tuple(listOfIdTuples)
    return identifiersTuplified

def getDuplicateInstanceTuple(self, instance):
        instanceTuple = self.getInstanceTuple(instance)
        path = self.getTuplePathInObjTree(instanceTuple)
        instanceTuple[2] = path
        return instanceTuple

def getInstanceTuple(self, instance):
        return tuple([type(instance).__name__, self.getInstanceIdentifiers(instance), instance])

#Will go through every dictionary in the object tree and return branching depth of the tuple
#if the tuple exists within the tree.
def getTuplePathInObjTree(self, instanceTuple, traversalList=[]):
    if(traversalList==[]):
        print('Trying to find Tuple match in Object Tree for tuple: ')
        print(instanceTuple)
    path = None
    branch = self.getBranchNode(traversalList = traversalList)
    print('Branch to be searched: ')
    print(branch)
    for branchTuple in branch.keys():
        if branchTuple[0] == instanceTuple[0] and branchTuple[1] == instanceTuple[1]:
            if(type(branchTuple[2]) == tuple):
                print('Found tuple match!')
                return branchTuple[2]
            print('Found tuple match!')
            print(traversalList)
            return traversalList
    for branchTuple in branch.keys():
        path = self.getTuplePathInObjTree(traversalList=traversalList+[branchTuple],instanceTuple=instanceTuple)
        if(path != None):
            return path
    if(traversalList == []):
        print('Tuple not found in tree!')
    return path

def makeObjectTree(self, traversalList=None, baseTuple=None):
    print('making tree')
    if(traversalList == None or baseTuple== None):
        baseTuple=tuple([type(self).__name__, self.getInstanceIdentifiers(self), self])
        traversalList=[baseTuple]
        self.objectTree = {baseTuple:{}}
        print('Tree Base Setup, getting Branches.')
    branchingDict = self.getBranches(traversalList)
    print('Got Branches.')
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
    print('before loop')
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
            print("originalPath: ")
            print(originalPath)
            print("traversalPath: ")
            print(traversalList)
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
    print('Object Tree: ')
    print(self.objectTree)
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
def primePolyTyping(self, identifierVariables=['identifier']):
    source_Polari = self.makeFile(name='definePolari', extension='py')
    source_dataStream = self.makeFile(name='dataStreams', extension='py')
    source_remoteEvent = self.makeFile(name='remoteEvents', extension='py')
    source_managedUserInterface = self.makeFile(name='managedUserInterface', extension='py')
    source_managedFile = self.makeFile(name='managedFile', extension='py')
    #managedApp and browserSourcePage share the same source file.
    source_managedAppANDbrowserSourcePage = self.makeFile(name='managedApp', extension='py')
    source_managedDatabase = self.makeFile(name='managedDB', extension='py')
    source_dataChannel = self.makeFile(name='dataChannels', extension='py')
    source_managedExecutable = self.makeFile(name='managedExecutable', extension='py')
    #polyTyped Object and variable are both defined in the same source file
    source_polyTypedObjectANDvariables = self.makeFile(name='polyTypedObject', extension='py')
    self.objectTyping = [
        polyTypedObject(sourceFiles=[source_Polari], className='Polari', identifierVariables = ['identifier'], objectReferencesDict={'managedApp':['manager'],'polyTypedObject':['manager']}, manager=self),
        polyTypedObject(sourceFiles=[source_dataStream], className='dataStream', identifierVariables = ['identifier'], objectReferencesDict={'managedApp':['dataStreamsToProcess','dataStreamsRequested','dataStreamsAwaitingResponse']}, manager=self),
        polyTypedObject(sourceFiles=[source_remoteEvent], className='remoteEvent', identifierVariables = ['identifier'], objectReferencesDict={'managedApp':['eventsToProcess','eventsToSend','eventsAwaitingResponse']}, manager=self),
        polyTypedObject(sourceFiles=[source_managedUserInterface], className='managedUserInterface', identifierVariables = ['identifier'], objectReferencesDict={'managedApp':['UIs']}, manager=self),
        polyTypedObject(sourceFiles=[source_managedFile], className='managedFile', identifierVariables = ['name','extension','Path'], objectReferencesDict={'managedApp':['AppFiles']}, manager=self),
        polyTypedObject(sourceFiles=[source_managedAppANDbrowserSourcePage], className='managedApp', identifierVariables = ['name'], objectReferencesDict={'managedApp':['subApps','manager'],'polyTypedObject':['manager']}, manager=self),
        polyTypedObject(sourceFiles=[source_managedAppANDbrowserSourcePage], className='browserSourcePage', identifierVariables = ['name','Path'], objectReferencesDict={'managedApp':['landingSourcePage','sourcePages']}, manager=self),
        polyTypedObject(sourceFiles=[source_managedDatabase], className='managedDatabase', identifierVariables = ['name','Path'], objectReferencesDict={'managedApp':['DB']}, manager=self),
        polyTypedObject(sourceFiles=[source_dataChannel], className='dataChannel', identifierVariables = ['name','Path'], objectReferencesDict={'managedApp':['serverChannel','localAppChannel'],'managedSourcePage':['']}, manager=self),
        polyTypedObject(sourceFiles=[source_managedExecutable], className='managedExecutable', identifierVariables = ['name', 'extension','Path'], objectReferencesDict={}, manager=self),
        polyTypedObject(sourceFiles=[source_polyTypedObjectANDvariables], className='polyTypedObject', identifierVariables = ['className'], objectReferencesDict={'managedApp':['objectTyping']}, manager=self),
        polyTypedObject(sourceFiles=[source_polyTypedObjectANDvariables], className='polyTypedVariable', identifierVariables = ['name','polyTypedObj'], objectReferencesDict={'polyTypedObject':['polyTypedVars']}, manager=self)
    ]
    #Goes through the objectTyping list to make sure that the object
    #that is 'self' was accounted for, adds a default typing if not.
    selfIsTyped = False
    for objTyp in self.objectTyping:
        if(objTyp.className == type(self).__name__):
            selfIsTyped = True
    if not selfIsTyped:
        source_self = self.makeFile(name=self.__module__, extension='py')
        self.addObjTyping(sourceFiles=[source_self], className=type(self).__name__, identifierVariables=identifierVariables, objectReferencesDict={})

def addObjTyping(self, sourceFiles, className, identifierVariables, objectReferencesDict={}):
    newTypingObj = polyTypedObject(sourceFiles=sourceFiles, className=className, identifierVariables=identifierVariables, objectReferencesDict=objectReferencesDict, manager=self)

def makeFile(self, name=None, extension=None):
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
    newFile.createFile()
    (self.managedFiles).append(newFile)

#In the case where this object is a Subordinate Object tree,
#it should reference the highest order manager to establish it's id.
def makeUniqueIdentifier(self, identifierVars=['identifier']):
    if(self.manager == None):
        identifiersList = (self.manager)
        self.identifier = 0
    else:
        (self.manager).makeUniqueIdentifier(identifierVars=identifierVars)

def numToBase64(self, num):
    byteNum = num.encode('ascii')
    b64Num = base64.b64encode(byteNum)
    return b64Num

def revertBase64numToInt(self, b64num):
    return b64num.decode('ascii')

#Types of operations on queries that can narrow down search criteria.
#Strict criteria run first because they narrow down options more quickly most consistently.
#relational criteria run second because they often narrow down options more than a subSet operation.
#subSet criteria run last because they 
#strict criteria (very restrictive) - Narrows to instances which carry only one specific value for a var.
#relational criteria (variably restrictive) - Narrows to instances which are determined to have a relation (Immediate connection through Object Tree) with a specified object.
#subSet criteria (less restrictive) - Narrows all instances down to a subset of possibilities of itself based on criteria.
#max - gets instances in tree holding the maximum numeric value for that variable.
#min - gets instances in tree holding the minimum numeric value for that variable.
# >,<,>=,<= - gets instances in tree based on numeric value in comparison to a specified value being compared.
# == - gets instances in tree if their variable is an exact match to the specifier passed.
#%+ - gets instances which have a post-fix matching the given specifier, and may have anything following that.
#+% - gets instances which have a pre-fix matching the given specifier
#+%+ - gets instances where any portion of the variables value matches the specifier
strictOperationTypes = [("max"),("min"),("==","specifier")]
relationalOperationTypes = [("hasChild","specifier"),("hasParent","specifier")]
subSetOperationTypes = [("specifier","%","specifier"),(">","specifier"),("<","specifier"),(">=","specifier"),("<=","specifier"),("%","specifier"),("specifier","%")]
allOperationTypes = strictOperationTypes + relationalOperationTypes + subSetOperationTypes
specialCharacters = ["=",">","<"]
orderingCharacters = [",","[","]","(",")",":"]
#Example Object Tree query: (className='testObj', "[identifier:(max), testVar:(==None), name:(a%c%)]")
def queryObjectTree(self, className, queryString):
    curType = None
    idName = None
    tempTuple = []
    tuplesList = []
    strictCommands = []
    subSetCommands = []
    relationalCommands = []
    varQuery = {}
    #Parsing Commands and putting them in appropriate order
    for objType in (self.manager).objectTyping:
        if(objType.className == className):
            curType = objType
            break
    if(curType == None):
        print("Object Type (Polytyping Object) not defined on the given manager object for ", curType)
        return
    #Parse through and eliminate all spaces, then get variable query sets
    i = 0
    varName = None
    cmdFound = False
    while i < len(queryString):
        cmdFound = False
        if(queryString[i] == ' '):
            continue
        else:
            for strCmd in strictCommands:
                if(strCmd[0] == 'specifier'):
                    continue
                else:
                    j = 0
                    while j < len(strCmd):
                        if((strCmd[0])[j:j+1] == queryString[i+j]):
                            if(j == len(strCmd) - 1):
                                strictCommands.append( tuple([]) )
                                cmdFound = True
                        else:
                            break
                        j += 1
            if(cmdFound == False):
                foundKeyChar = False
                j = 0
                while (not foundKeyChar) or i+j < len(queryString):
                    if(queryString[i+j] in orderingCharacters):
                        if(queryString[i+j:i+j+2] == ":("):
                            #Get the word before this ':', which should be the variable name, load it onto varName.
                            varName = queryString[i:i+j-1]
                            i = (i+j+2)
                            break
                    j += 1
        if(not cmdFound):
            i += 1
    

class testObj:
    @managerObject
    def __init__(self):
        self.testVar = None
        self.name = "abcdef"
        self.identifier = 1
        self.primePolyTyping()
        self.addObjTyping(sourceFiles=[os.path.basename(__file__)], className=type(self).__name__, identifierVariables=['identifier'])
        pass

someObj = testObj()
print(someObj.__dict__)