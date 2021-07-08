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
#from polyTyping import *
from functools import wraps
from polariList import *
import types, inspect, base64


def treeObjectInit(init):
    #Note: For objects instantiated using this Decorator, MUST USER KEYWORD ARGUMENTS NOT POSITIONAL, EX: (manager=mngObj, id='base64Id')
    @wraps(init)
    def new_init(self, *args, **keywordargs):
        #print('Initial kwargs: ', keywordargs)
        treeObject.__init__(self, *args, **keywordargs)
        objectParamsTuple = init.__code__.co_varnames
        keywordArgsToPass = {}
        for elem in keywordargs.keys():
            if elem in objectParamsTuple:
                keywordArgsToPass[elem] = keywordargs[elem]
        #print('Passed kwargs: ', keywordArgsToPass)
        new_init = init(self, *args, **keywordArgsToPass)
    return new_init

BASE_CHARS = tuple("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
BASE_DICT = dict((c, v) for v, c in enumerate(BASE_CHARS))
BASE_LEN = len(BASE_CHARS)

#Defines a treeObject, which allocates all variables and functions necessary for
#an object to be a subordinate object on an Object Tree.
class treeObject:
    #Note: For objects instantiated using this Decorator, MUST USER KEYWORD ARGUMENTS NOT POSITIONAL, EX: (manager=mngObj, id='base64Id')
    def __init__(self, *args, **keywordargs):
        #print('Name of the treeObject: ', self.__class__.__name__)
        #print('args: ', args)
        #print('keywordargs: ', keywordargs)
        #Adding on the necessary variables for a tree object, in the case they are not defined.
        if not 'manager' in keywordargs.keys():
            setattr(self, 'manager', None)
        if not 'id' in keywordargs.keys():
            setattr(self, 'id', None)
        if not 'branch' in keywordargs.keys():
            setattr(self, 'branch', None)
        if not 'inTree' in keywordargs.keys():
            setattr(self, 'inTree', None)
        #print('parameters list: ', parameters, ' positional args: ', args, ' and keyword args: ', keywordargs)
        for name in keywordargs.keys():
            #print('In parameters, found attribute ', name, ' with value ', keywordargs[name])
            if(name=='manager' or name=='id' or name=='branch' or name=='inTree'):
                setattr(self, name, keywordargs[name])
        if(self.id == None):
            self.makeUniqueIdentifier()

    def __setattr__(self, name, value):
        if(type(value).__name__ == 'list'):
            #print("converting from list with value ", value, " to a polariList.")
            #Instead of initializing a polariList, we try to just cast the list to be type polariList.
            value = polariList(value)
            value.jumpstart(treeObjInstance=self, varName=name)
            #print("Set list value to be polariList: ", value)
        #Case where the current branch that self is meant to be placed on has not yet been defined
        #*the branch must be defined BEFORE the manager value is set.
        #After a manager object is assigned, ensure a polyTypedObject exists for the given object self.
        if(not hasattr(self, 'manager') or name == 'manager' or not hasattr(self, 'branch') or name == 'branch'):
            if(name == 'branch'):
                if(type(value) == tuple):
                    branchType = type(value[2]).__name__
                    #Confirm the value that should be an object is not a standard type or ignored type.
                    if(not branchType in dataTypesPython and not branchType in ignoredObjectsPython or branchType == "NoneType"):
                        #TODO Confirm that the value being assigned has a treeObject base type.
                        super(treeObject, self).__setattr__(name, value[2])
                        if(hasattr(self, 'manager')):
                            if(self.manager != None):
                                self.managerSet(potentialManager=self.manager)
                        return
                    else:
                        print("Attempted to connect to a branch with invalid value in tuple - ", value, " with type - ", type(value[2]).__name__)
                else:
                    branchType = type(value).__name__
                    #Confirm the value that should be an object is not a standard type or ignored type.
                    if(not branchType in dataTypesPython and not branchType in ignoredObjectsPython or branchType == "NoneType"):
                        #TODO Confirm that the value being assigned has a treeObject base type.
                        super(treeObject, self).__setattr__(name, value)
                        if(hasattr(self, 'manager')):
                            if(self.manager != None):
                                self.managerSet(potentialManager=self.manager)
                        return
                    else:
                        print("Attempted to connect to a branch with invalid value in tuple - ", value, " with type - ", type(value).__name__)
            #Handle cases where the manager was previously something else, but it has been taken by another manager.
            elif(name == 'manager'):
                if(hasattr(self, 'manager')):
                    if(self.manager != value and self.manager != None):
                        #TODO Write code to handle taking branches off of one manager and onto another.
                        print('The manager of the object ', self, 'has been changed from ', self.manager, ' to ', value)
                        pass
                if(hasattr(self, 'branch')):
                    if(self.branch != None):
                        self.managerSet(potentialManager=value)
                        return
                super(treeObject, self).__setattr__(name, value)
                return
        elif(self.manager == None or not hasattr(self, 'branch')):
            super(treeObject, self).__setattr__(name, value)
            return
        if(type(value).__name__ in dataTypesPython and type(value) != list):
            super(treeObject, self).__setattr__(name, value)
            return
        if(self.__class__.__name__ == 'polyTypedObject' or self.__class__.__name__ == 'polyTypedVariable'):
            super(treeObject, self).__setattr__(name, value)
            return
        if(self.manager != None and self.branch != None):
            #print("Setting non-standard value on treeObject after manager is set and branch is set.")
            selfPolyObj = self.manager.getObjectTyping(self.__class__)
            selfIds = self.manager.getInstanceIdentifiers(value)
            selfTuple = self.manager.getInstanceTuple(self)
            selfPath = self.manager.getTuplePathInObjTree(instanceTuple=selfTuple)
            #Handles the case where the current treeObject already exists in the current manager's Tree.
            if(selfPath != None):
                #print("Found appropriate path for treeObject")
                polyObj = self.manager.getObjectTyping(self.__class__)
                if value == None:
                    pass
                elif(type(value).__name__ == "list" or type(value).__name__ == "polariList"):
                    #print("Going through list variable assignment for var ", name ," post-init on treeObject using list ", value)
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
                        ids = self.manager.getInstanceIdentifiers(inst)
                        instPath = self.manager.getTuplePathInObjTree(instanceTuple=tuple([inst.__class__.__name__, ids, inst]))
                        if instPath == None:
                            #print("found an instance with no existing branch, now creating branch on manager: ", inst)
                            newBranch = tuple([inst.__class__.__name__, ids, inst])
                            self.manager.addNewBranch(traversalList=selfPath, branchTuple=newBranch)
                            #Make sure the new branch has the current manager and self as it's origin branch set on it.
                            if(self != inst.branch):
                                inst.branch = self
                            if(self != inst.manager):
                                inst.manager = self.manager
                        elif len(instPath) <= len(selfPath) + 1:
                            #print("found an instance already in the objectTree at the correct location:", inst)
                            pass
                        else:
                            #print("Found an instance at a higher level which is now being moved to be a branch on the managed: ", inst)
                            duplicateBranchTuple = tuple([inst.__class__.__name__, ids, tuple([])]) 
                            self.manager.replaceOriginalTuple(self.manager, originalPath = instPath, newPath=selfPath + [duplicateBranchTuple], newTuple=duplicateBranchTuple)
                            #Make sure the new branch has the current manager and self as it's origin branch set on it.
                            if(self != inst.branch):
                                inst.branch = self
                            if(self != inst.manager):
                                inst.manager = self.manager
                            #TODO make a function that swaps any branching on the original tuple to be on the new location.
                    #All other cases should have been eliminated, this should be dealing with object instances
                    #that have a treeObject base and are non-ignored, being assigned to a single variable.
                    else:
                        #print('Adding one object as variable, ', name ,' to the manager with value: ', value)
                        #if(self.identifiersComplete(value)):
                        ids = self.manager.getInstanceIdentifiers(value)
                        valuePath = self.manager.getTuplePathInObjTree(instanceTuple=tuple([value.__class__.__name__, ids, value]))
                        if(valuePath == None):
                            #add the new Branch
                            #print("found an instance with no existing branch, now creating branch on manager: ", value)
                            newBranch = tuple([value.__class__.__name__, ids, value])
                            self.manager.addNewBranch(traversalList=selfPath, branchTuple=newBranch)
                            #Make sure the new branch has the current manager and self as it's origin branch set on it.
                            if(self != value.branch):
                                value.branch = self
                            if(self.manager != value.manager):
                                value.manager = self.manager
                        elif len(valuePath) <= len(selfPath) + 1:
                            #print("found an instance already in the objectTree at the correct location:", value)
                            #Do nothing, because the branch is already accounted for.
                            pass
                        else:
                            #add as a duplicate branch
                            #print("Found an instance at a higher level which is now being moved to be a branch on the managed: ", value)
                            duplicateBranchTuple = tuple([value.__class__.__name__, ids, tuple(valuePath)])
                            self.replaceOriginalTuple(self.manager, originalPath=valuePath, newPath=selfPath + [duplicateBranchTuple], newTuple=duplicateBranchTuple)
                            #Make sure the new branch has the current manager and self as it's origin branch set on it.
                            if(self != value.branch):
                                value.branch = self
                            if(self.manager != value.manager):
                                value.manager = self.manager
                            #TODO make a function that swaps any branching on the original tuple to be on the new location.
                #Handles the case where a single variable is being set.
                else:
                    #print("Going through single variable assignment for var ", name ," post-init on treeObject using value ", value)
                    accountedObjectType = False
                    accountedVariableType = False
                    if(type(value).__class__.__name__ in polyObj.objectReferencesDict):
                        accountedObjectType = True
                        print("Class type ", type(value).__class__.__name__, " accounted for in object typing for ", self.__class__.__name__)
                        if(polyObj.objectReferencesDict[type(value).__class__.__name__]):
                            accountedVariableType = True
                            print("Accounted for class type ", value, " as sole value in variable ", name)
                    newpolyObj = self.manager.getObjectTyping(classObj=value.__class__)
                    managerPolyTyping = self.manager.getObjectTyping(self.manager.__class__)
                    if(not accountedVariableType):
                        managerPolyTyping.addToObjReferenceDict(referencedClassObj=value.__class__, referenceVarName=name)
                    ids = self.manager.getInstanceIdentifiers(value)
                    valuePath = self.manager.getTuplePathInObjTree(instanceTuple=tuple([newpolyObj.className, ids, value]))
                    #print('Setting attribute to a value: ', value)
                    #print('Found object: "', value ,'" being assigned to an undeclared reference variable: ', name, 'On object: ', self)
                    newpolyObj = self.manager.getObjectTyping(value.__class__)
                    if(type(value).__name__ == "list" or type(value).__name__ == "polariList"):
                        #Adding a list of objects
                        for inst in value:
                            #print('Adding one object as element in a list variable, ', name ,' to the manager with value: ', inst)
                            #if(self.identifiersComplete(inst)):
                            ids = self.manager.getInstanceIdentifiers(inst)
                            instPath = self.manager.getTuplePathInObjTree(instanceTuple=tuple([inst.__class__.__name__, ids, inst]))
                            #Case where the existing tuple is at the same level as this object or a lower object, in this case we place a duplicate while leaving the original alone.
                            #Case where the object has no existing tuple in the tree.
                            if instPath == None:
                                #print("found an instance with no existing branch, now creating branch on manager: ", inst)
                                newBranch = tuple([inst.__class__.__name__, ids, inst])
                                self.addNewBranch(traversalList=selfPath, branchTuple=newBranch)
                                #Make sure the new branch has the current manager set on it.
                                if(self.manager != inst.manager):
                                    inst.manager = self.manager
                            elif len(instPath) <= len(selfPath) + 1:
                                #print("found an instance already in the objectTree at the correct location:", inst)
                                pass
                            else:
                                #print("Found an instance at a higher level which is now being moved to be a branch on the managed: ", inst)
                                duplicateBranchTuple = tuple([inst.__class__.__name__, ids, tuple([])]) 
                                self.manager.replaceOriginalTuple(self.manager, originalPath = instPath, newPath=selfPath + [duplicateBranchTuple], newTuple=duplicateBranchTuple)
                                #Make sure the new branch has the current manager set on it.
                                if(self.manager != inst.manager):
                                    inst.manager = self.manager
                                #TODO make a function that swaps any branching on the original tuple to be on the new location.
                    else:
                        #print('Adding one object as variable, ', name ,' to the manager with value: ', value)
                        #if(self.identifiersComplete(value)):
                        ids = self.manager.getInstanceIdentifiers(value)
                        valuePath = self.manager.getTuplePathInObjTree(instanceTuple=tuple([value.__class__.__name__, ids, value]))
                        if(valuePath == None):
                            #add the new Branch
                            #print("found an instance with no existing branch, now creating branch on manager: ", value)
                            newBranch = tuple([value.__class__.__name__, ids, value])
                            self.manager.addNewBranch(traversalList=selfPath, branchTuple=newBranch)
                            #Make sure the new branch has the current manager set on it.
                            if(self.manager != value.manager):
                                value.manager = self.manager
                        elif(len(valuePath) <= len(selfPath) + 1):
                            #print("found an instance already in the objectTree at the correct location:", value)
                            #Do nothing, because the branch is already accounted for.
                            pass
                        else:
                            #add as a duplicate branch
                            #print("Found an instance at a higher level which is now being moved to be a branch on the managed: ", value)
                            duplicateBranchTuple = tuple([value.__class__.__name__, ids, tuple(valuePath)])
                            self.manager.replaceOriginalTuple(self, originalPath=valuePath, newPath=[duplicateBranchTuple], newTuple=duplicateBranchTuple)
                            #Make sure the new branch has the current manager set on it.
                            if(self.manager != value.manager):
                                value.manager = self.manager
                            #TODO make a function that swaps any branching on the original tuple to be on the new location.
            else:
                print("selfPath was not found in tree for object ", self)
        super(treeObject, self).__setattr__(name, value)


    #A function that triggers when the manager has just been set on the object instance
    #This first goes in and ascertains that the object has indeed been added to the
    #object tree.  currentBranchObject should be the treeObject instance that self
    #is supposed to be branching off of, and potentialManager is the manager that is
    #supposed to be set.
    def managerSet(self, potentialManager):
        #print("Calling managerSet for treeObject: ", self)
        #Checks that the object's manager has been set and is a valid manager.
        hasManager = False
        if(potentialManager != None):
            for parentObj in (potentialManager.__class__).__bases__:
                if(parentObj.__name__ == 'managerObject'):
                    hasManager = True
                    break
        hasBranch = False
        if(hasattr(self, 'branch')):
            #Handles the case where the branch is coming off of the manager itself.
            #TODO Figure out why setting branch as the manager causes infinite loop
            if(self.branch == potentialManager):
                hasBranch = True
            for parentObj in (self.branch.__class__).__bases__:
                #print('parent object name for branch, ', self.branch, ' object instance:', parentObj.__name__)
                if(parentObj.__name__ == 'treeObject'):
                    hasBranch = True
                    break
        if(not hasManager):
            print("ERROR: Called managerSet function, but manager has no valid object instance with parent managerObject.", self, ".")
        if(not hasBranch):
            print("ERROR: Called managerSet function, but no branch was defined on the object before running function on object - ", self)
        if not hasManager or not hasBranch:
            return False
        selfTreeTuple = potentialManager.getInstanceTuple(self)
        #print("Getting self path in setManager.")
        selfTreePath = potentialManager.getTuplePathInObjTree(selfTreeTuple)
        branchTreeTuple = potentialManager.getInstanceTuple(self.branch)
        #print("Getting branch path in setManager.")
        branchTreePath = potentialManager.getTuplePathInObjTree(instanceTuple=branchTreeTuple)
        #Checks that the manager has a valid polyTyping for this treeObject.
        selfPolyTyping = potentialManager.getObjectTyping(classObj=self.__class__)
        branchPolyTyping = potentialManager.getObjectTyping(classObj=self.branch.__class__)
        if(selfPolyTyping == None or branchPolyTyping == None):
            #print("Could not properly retrieve or set polyTyping on the manager ", potentialManager, " for objects of type ", self.__class__.__name__)
            return False
        #Handles the case where self has not yet been allocated onto the tree anywhere.
        if(branchTreePath == None):
            #print("The object's branch instance ", self.branch, " has not yet been added to the tree.")
            return False
        elif(selfTreePath == None):
            #print("Adding new branch in managerSet using path: ", branchTreePath, " and tuple: ", selfTreeTuple)
            potentialManager.addNewBranch(traversalList=branchTreePath, branchTuple=selfTreeTuple)
            selfTreePath = potentialManager.getTuplePathInObjTree(selfTreeTuple)
            #print("Placed new branch into tree using traversalList '", branchTreePath, "' and selfTreeTuple '", selfTreeTuple)
            #print("The new branch's path is: ", selfTreePath)
            if(selfTreePath == None):
                #print("ERROR: Attempted to place self into tree for instance ", self, " by branching from instance ", self.branch, " but failed.")
                return
        #Retrieves the Branching off of the current object
        selfTreePath = potentialManager.getTuplePathInObjTree(selfTreeTuple)
        #print("selfTreePath in setManager after placing self on Tree: ", selfTreePath)
        selfTreeBranch = potentialManager.getBranchNode(traversalList = selfTreePath)
        #print("selfTreeBranch in setManager: ", selfTreeBranch)
        #Goes through all attributes on the object, and loads them or their duplicates
        #onto the branch for this given instance in the tree.
        for someAttrKey in self.__dict__:
            #If it is the manager attribute, we ignore it since the manager is the tree's base.
            if(someAttrKey == "manager"):
                continue
            someAttr = getattr(self, someAttrKey)
            atrType = type(someAttr).__name__
            if(atrType in dataTypesPython and atrType != 'list' and atrType != 'polariList'):
                continue
            atrTypeList = []
            #START OF TREE MANAGEMENT FOR TREEOBJECTS IN LISTS
            #If it is a list, get a list of all referenced object types in the list.
            if(type(someAttr).__name__ == "list" or type(someAttr).__name__ == "polariList"):
                for someValue in someAttr:
                    #Make sure the type of each treeObject in the list is recorded.
                    if(type(someValue).__name__ in dataTypesPython):
                        continue
                    elif(not type(someValue).__name__ in atrTypeList):
                        atrTypeList.append(type(someValue).__name__)
                    #print("Analyzing someValue in list in managerSet.")
                    #Ensure polyTyping object exists for the value
                    valuePolyTyping = potentialManager.getObjectTyping(classInstance=someValue)
                    if(valuePolyTyping != None):
                        #Generate a tree tuple
                        valueInstanceTuple = potentialManager.getInstanceTuple(someValue)
                        valueTreePath = potentialManager.getTuplePathInObjTree(valueInstanceTuple)
                        valueIds = potentialManager.getInstanceIdentifiers(someValue)
                        #If the value exists anywhere in the tree already.
                        #continue
                        if(valueTreePath != None):
                            #continue
                            #If the value's tuple is not anywhere in the current branch
                            if(not valueInstanceTuple in selfTreeBranch.keys()):
                                #print("Adding a branch of an already existing tuple for object: ", someValue)
                                #Check the depth of the original and the depth + 1 of the selfBranch
                                #If the depth + 1 of current branch is less than original swap original to
                                #this branch and place duplicate in the old location.
                                originalDepth = len(valueTreePath)
                                potentialDepth = len(selfTreePath) + 1
                                if(potentialDepth < originalDepth):
                                    #Change original to duplicate, place original on this branch
                                    duplicateBranchTuple = tuple([someValue.__class__.__name__, valueIds, tuple(valueTreePath)])
                                    potentialManager.replaceOriginalTuple(potentialManager, originalPath=valueTreePath, newPath=branchTreePath + [duplicateBranchTuple], newTuple=duplicateBranchTuple)
                                else:
                                    #Place duplicate on the current branch.
                                    duplicateBranchTuple = tuple([someValue.__class__.__name__, valueIds, tuple(valueTreePath)])
                                    potentialManager.addDuplicateBranch(traversalList=branchTreePath, branchTuple=duplicateBranchTuple)
                            else:
                                print("Value ", someValue, " in list attribute ", someAttrKey, "was already in the correct location on tree before managerSet.")
                        else:
                            #TODO the following code in this else block causes everything to break.
                            #print("potential break reason 1: selfTreePath value: ", selfTreePath)
                            #print("potential break reason 2: valueInstanceTuple value: ", valueInstanceTuple)
                            #print("potential break reason 3: someValue value: ", someValue)
                            #continue
                            if(type(someValue).__name__ != "polyTypedVariable"):
                                #The tuple does not exist anywhere in the tree, so we simply place a new branch.
                                potentialManager.addNewBranch(traversalList=selfTreePath, branchTuple=valueInstanceTuple)
                                if(self != someValue.branch):
                                    #print("Adding self ", self, " to be branch value of child ", someValue)
                                    someValue.branch = self
                                if(self != someValue.manager):
                                    someValue.manager = self.manager
                                #print("Adding a new tuple to the object tree from a List in managerSet: ", valueInstanceTuple)
            #END OF TREE MANAGEMENT FOR TREEOBJECTS IN LISTS OR TUPLES
            #
            #START OF TREE MANAGEMENT FOR TREEOBJECTS DIRECTLY ASSIGNED TO ATTRIBUTES
            else:
                #Make sure the type of each treeObject in the list is recorded.
                if(not type(someAttr).__name__ in dataTypesPython):
                    if(not type(someAttr).__name__ in atrTypeList):
                        atrTypeList.append(type(someAttr).__name__)
                #Ensure polyTyping object exists for the value
                valuePolyTyping = potentialManager.getObjectTyping(classInstance=someAttr)
                if(valuePolyTyping != None):
                    #Generate a tree tuple
                    valueInstanceTuple = potentialManager.getInstanceTuple(someAttr)
                    #Check if the tuple exists somewhere in the current branch
                    tupleFoundInBranch = False
                    tupleFoundInTree = False
                    for someTuple in selfTreeBranch:
                        #If is in the current branch, ignore it and move to the next iteration.
                        if(not someTuple[0] == valueInstanceTuple[0] and someTuple[1] == valueInstanceTuple[1]):
                            tupleFoundInBranch = True
                            tupleFoundInTree = True
                            break
                    valueTreePath = potentialManager.getTuplePathInObjTree(valueInstanceTuple)
                    if(valueTreePath == None):
                        tupleFoundInTree = False
                        #print("Could not retrieve path from manager for the tuple: ", valueInstanceTuple, " which was set as a value on the object ", self)
                    #If it is NOT in the branch, check to see if it is in the tree at all.
                    if(not tupleFoundInBranch):
                        if(valueTreePath != None):
                            tupleFoundInTree = True
                    ids = potentialManager.getInstanceIdentifiers(someAttr)
                    if(tupleFoundInTree):
                        if(not tupleFoundInBranch):
                            #Check the depth of the original and the depth + 1 of the selfBranch
                            #If the depth + 1 of current branch is less than original swap original to
                            #this branch and place duplicate in the old location.
                            originalDepth = len(valueTreePath)
                            potentialDepth = len(selfTreePath) + 1
                            if(potentialDepth < originalDepth):
                                #Change original to duplicate, place original on this branch
                                duplicateBranchTuple = tuple([someAttr.__class__.__name__, ids, tuple(valueTreePath)])
                                potentialManager.replaceOriginalTuple(potentialManager, originalPath=valueTreePath, newPath=selfTreePath + [duplicateBranchTuple], newTuple=duplicateBranchTuple)
                            else:
                                #Place duplicate on the current branch.
                                duplicateBranchTuple = tuple([someAttr.__class__.__name__, ids, tuple(valueTreePath)])
                                potentialManager.addNewBranch(traversalList=branchTreePath, branchTuple=duplicateBranchTuple)
                    else:
                        #The tuple does not exist anywhere in the tree, so we simply place it in the branch.
                        potentialManager.addNewBranch(traversalList=branchTreePath, branchTuple=valueInstanceTuple)
                        #print("Adding a new tuple to the object tree in managerSet: ", valueInstanceTuple)
        #END OF TREE MANAGEMENT FOR TREEOBJECTS IN LISTS OR TUPLES
        #Return True to indicate the manager was successfully set.
        return True
                
                        

    #In the case where this object is a Subordinate Object tree,
    #it should reference the highest order manager to establish it's id.
    #In the case where this object is a Subordinate Object tree,
    #it should reference the highest order manager to establish it's id.
    def makeUniqueIdentifier(self, N=9):
        import random
        if(self.manager == None):
            print("For object ", self.__class__.__name__, " there is no assigned manager!!")
            self.id = None
            return
        else:
            idString = ''
            for i in range(0,N):
                num = random.randint(0,63)
                idString += self.base62Encode(num = num)
            #print('current object: ', self)
            #print('Object\'s manager: ', self.manager)
            #print('manager idList: ', self.manager.idList)
            if(not idString in self.manager.idList):
                self.id = idString
                (self.manager.idList).append(idString)
                return
            else:
                self.id = self.makeUniqueIdentifier(self, N=N+1)
                return

    # -- This section based on Code shared publically on Stack Overflow put out by 'Sepero' (Thank you sir) --
    #link to source: https://stackoverflow.com/questions/1119722/base-62-conversion

    def base62Decode(self, string):
        num = 0
        for char in string:
            num = num * BASE_LEN + BASE_DICT[char]
        return num

    def base62Encode(self, num):
        if not num:
            return BASE_CHARS[0]
        encoding = ""
        while num:
            num, rem = divmod(num, BASE_LEN)
            encoding = BASE_CHARS[rem] + encoding
        return encoding

    #         ---------------------------------------------------------------------------