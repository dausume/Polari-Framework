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
import types, inspect, base64

standardTypesPython = ['str','int','float','complex','list','tuple','range','dict',
'set','frozenset','bool','bytes','bytearray','memoryview', 'type', 'NoneType', 'TextIOWrapper']
ignoredObjectsPython = ['struct_time', 'API']
ignoredObjectImports = {'falcon':['API'], 'time':['struct_time']}
dataTypesPython = standardTypesPython + ignoredObjectsPython
dataTypesJS = ['undefined','Boolean','Number','String','BigInt','Symbol','null','Object','Function']
dataTypesJSON = ['String','Number','Object','Array','Boolean','null']
dataAffinitiesSqlite = ['NONE','INTEGER','REAL','TEXT','NUMERIC']

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
        #print('parameters list: ', parameters, ' positional args: ', args, ' and keyword args: ', keywordargs)
        for name in keywordargs.keys():
            #print('In parameters, found attribute ', name, ' with value ', keywordargs[name])
            if(name=='manager' or name=='id'):
                setattr(self, name, keywordargs[name])
        if(self.id == None):
            self.makeUniqueIdentifier()

    def __setattr__(self, name, value):
        if(type(value).__name__ in dataTypesPython):
            #print('setting value in treeObj in a standard dataType..')
            super(treeObject, self).__setattr__(name, value)
            return
        #After a manager object is assigned, ensure a polyTypedObject exists for the given object self.
        if(not hasattr(self, 'manager') or name == 'manager'):
            #Handle cases where the manager was previously something else, but it has been taken by another manager.
            if(hasattr(self, 'manager')):
                if(self.manager != value and self.manager != None):
                    print('The manager of the object ', self, 'has been changed from ', self.manager, ' to ', value)
            super(treeObject, self).__setattr__(name, value)
            return
        if(self.manager != None):
            selfPolyObj = self.manager.getObjectTyping(self.__class__)
            selfIds = self.manager.getInstanceIdentifiers(value)
            selfPath = self.manager.getTuplePathInObjTree(instanceTuple=tuple([selfPolyObj.className, selfIds, self]))
            if(selfPath != None):
                if name in selfPolyObj.objectReferencesDict:
                    if(value == None or value == []):
                        pass
                    elif(type(value) == list):
                        #Adding a list of objects
                        for inst in value:
                            #print('Adding one object as element in a list variable, ', name ,' to the manager with value: ', inst)
                            #if(self.identifiersComplete(inst)):
                            ids = self.getInstanceIdentifiers(inst)
                            instPath = self.getTuplePathInObjTree(instanceTuple=tuple([inst.__class__.__name__, ids, inst]))
                            if len(instPath) <= len(selfPath) + 1:
                                #print("found an instance already in the objectTree at the correct location:", inst)
                                pass
                            elif instPath == None:
                                #print("found an instance with no existing branch, now creating branch on manager: ", inst)
                                newBranch = tuple([inst.__class__.__name__, ids, inst])
                                self.addNewBranch(traversalList=[], branchTuple=newBranch)
                            else:
                                #print("Found an instance at a higher level which is now being moved to be a branch on the managed: ", inst)
                                duplicateBranchTuple = tuple([inst.__class__.__name__, ids, tuple([])]) 
                                self.replaceOriginalTuple(self, originalPath = instPath, newPath=selfPath + [duplicateBranchTuple], newTuple=duplicateBranchTuple)
                    else:
                        print('Adding one object as variable, ', name ,' to the manager with value: ', value)
                        #if(self.identifiersComplete(value)):
                        ids = self.getInstanceIdentifiers(value)
                        valuePath = self.getTuplePathInObjTree(instanceTuple=tuple([value.__class__.__name__, ids, value]))
                        if len(valuePath) <= len(selfPath) + 1:
                            print("found an instance already in the objectTree at the correct location:", value)
                            #Do nothing, because the branch is already accounted for.
                            pass
                        elif(valuePath == None):
                            #add the new Branch
                            print("found an instance with no existing branch, now creating branch on manager: ", value)
                            newBranch = tuple([value.__class__.__name__, ids, value])
                            self.addNewBranch(traversalList=[], branchTuple=newBranch)
                        else:
                            #add as a duplicate branch
                            print("Found an instance at a higher level which is now being moved to be a branch on the managed: ", value)
                            duplicateBranchTuple = tuple([value.__class__.__name__, ids, tuple(valuePath)])
                            self.replaceOriginalTuple(self, originalPath=valuePath, newPath=selfPath + [duplicateBranchTuple], newTuple=duplicateBranchTuple)
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
                            instPath = self.getTuplePathInObjTree(instanceTuple=tuple([inst.__class__.__name__, ids, inst]))
                            #Case where the existing tuple is at the same level as this object or a lower object, in this case we place a duplicate while leaving the original alone.
                            if len(instPath) <= len(selfPath) + 1:
                                print("found an instance already in the objectTree at the correct location:", inst)
                                pass
                            #Case where the object has no existing tuple in the tree.
                            elif instPath == None:
                                print("found an instance with no existing branch, now creating branch on manager: ", inst)
                                newBranch = tuple([inst.__class__.__name__, ids, inst])
                                self.addNewBranch(traversalList=[], branchTuple=newBranch)
                            else:
                                print("Found an instance at a higher level which is now being moved to be a branch on the managed: ", inst)
                                duplicateBranchTuple = tuple([inst.__class__.__name__, ids, tuple([])]) 
                                self.replaceOriginalTuple(self, originalPath = instPath, newPath=selfPath + [duplicateBranchTuple], newTuple=duplicateBranchTuple)
                    else:
                        print('Adding one object as variable, ', name ,' to the manager with value: ', value)
                        #if(self.identifiersComplete(value)):
                        ids = self.getInstanceIdentifiers(value)
                        valuePath = self.getTuplePathInObjTree(instanceTuple=tuple([value.__class__.__name__, ids, value]))
                        if len(valuePath) <= len(selfPath) + 1:
                            print("found an instance already in the objectTree at the correct location:", value)
                            #Do nothing, because the branch is already accounted for.
                            pass
                        elif(valuePath == None):
                            #add the new Branch
                            print("found an instance with no existing branch, now creating branch on manager: ", value)
                            newBranch = tuple([value.__class__.__name__, ids, value])
                            self.addNewBranch(traversalList=[], branchTuple=newBranch)
                        else:
                            #add as a duplicate branch
                            print("Found an instance at a higher level which is now being moved to be a branch on the managed: ", value)
                            duplicateBranchTuple = tuple([value.__class__.__name__, ids, tuple(valuePath)])
                            self.replaceOriginalTuple(self, originalPath=valuePath, newPath=[duplicateBranchTuple], newTuple=duplicateBranchTuple)
                #print("Finished setting value of ", name, " to be ", value)
        super(treeObject, self).__setattr__(name, value)

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