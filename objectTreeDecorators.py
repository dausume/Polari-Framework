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

#Defines a Decorator @treeObject, which allocates all variables and functions necessary for
#an object to be a subordinate object on an Object Tree.
def treeObject(init):
    parameters = inspect.getfullargspec(init)[0]

    #Note: For objects instantiated using this Decorator, MUST USER KEYWORD ARGUMENTS NOT POSITIONAL, EX: (manager=mngObj, id='base64Id')
    @wraps(init)
    def new_init(self, *args, **keywordargs):
        initParametersDict = {}
        #Adding on the necessary variables for a tree object, in the case they are not defined.
        if not 'manager' in keywordargs.keys() and not 'manager' in zip(parameters[1:], args):
            setattr(self, 'manager', None)
        if not 'id' in zip(parameters[1:], args) and not 'id' in keywordargs.keys():
            setattr(self, 'id', None)
        #print('parameters list: ', parameters, ' positional args: ', args, ' and keyword args: ', keywordargs)
        for name in keywordargs.keys():
            #print('In parameters, found attribute ', name, ' with value ', keywordargs[name])
            if(name=='manager'):
                setattr(self, name, keywordargs[name])
                #print('setting manager in init for object ', self, ' as object ', self.manager)
            if(name=='id'):
                setattr(self, name, keywordargs[name])
            if(name in parameters):
                initParametersDict[name] = keywordargs[name]
        for name, value in zip(parameters[1:], args):
            #print('In parameters, found attribute ', name, ' with value ', value)
            if(name=='manager' or name=='id'):
                setattr(self, name, value)
            if(name in parameters):
                initParametersDict[name] = value
        #Adding on all of the functions and overrides needed for acting as a manager object.
        setattr( self, '__setattr__', types.MethodType(__setattr__, self) )
        setattr( self, 'makeUniqueIdentifier', types.MethodType(makeUniqueIdentifier, self) )
        setattr( self, 'base62Decode', types.MethodType(base62Decode, self) )
        setattr( self, 'base62Encode', types.MethodType(base62Encode, self) )
        if(self.id == None):
            self.makeUniqueIdentifier()
        #print("For object ", self.__class__.__name__, " the id before running object-specific init is: ", self.id)
        new_init = init(self, **initParametersDict)
    return new_init

def __setattr__(self, name, value):
    #Catch manager before value is assigned, and place this object instance into the object tree at it's base.
    if(name == 'manager'):
        if(self.manager != None):
            if(self.manager.idList != None and self.manager.objectTyping != None and self.manager.cloudIdList != None):
                polyObj = self.manager.objectTyping[type(self).__name__]
                #Adding one object
                if(self.manager.identifiersComplete(value)):
                    ids = self.manager.getInstanceIdentifiers(value)
                    valuePath = self.manager.getTuplePathInObjTree(instanceTuple=tuple([polyObj.className, ids, value]))
                    if(valuePath == []):
                        #Do nothing, because the branch is already accounted for.
                        pass
                    elif(valuePath == None):
                        #add the new Branch
                        newBranch = tuple([polyObj.className, ids, value])
                        self.manager.addNewBranch(traversalList=[], branchTuple=newBranch)
                    else:
                        #add as a duplicate branch
                        duplicateBranchTuple = tuple([polyObj.className, ids, tuple(valuePath)])
                        self.manager.replaceOriginalTuple(self, originalPath=valuePath, newPath=[duplicateBranchTuple], newTuple=duplicateBranchTuple)
            else:
                print('Value set to be manager is invalid, a manager object would always have lists or empty list values for variables idList, objectTyping, and cloudIdList')
                self.manager = None
        #In this case, manager has just been set to None, meaning we are removing it from it's previous object tree.
        else:
            polyObj = self.manager.objectTyping[type(self).__name__]
            #Adding one object
            if(self.manager.identifiersComplete(value)):
                ids = self.manager.getInstanceIdentifiers(value)
                valuePath = self.manager.getTuplePathInObjTree(instanceTuple=tuple([polyObj.className, ids, value]))
            #Get the tuple and all of it's duplicates, then remove them from the object tree.
            #NEED A FUNCTION TO RETRIEVE ALL DEUPLICATES OF A TUPLE
    super(setattr, self).__setattr__(name, value)
    if(self.manager != None):
        polyObj = self.manager.objectTyping[type(self).__name__]
        #In polyObj 'polyObj.className' potential references exist for this object.
        #Here, we get each variable that is a reference or a list of references to a
        #particular type of object.
        if name in polyObj.objectReferencesDict:
            if(value == None or value == []):
                pass
            elif(type(value) == list):
                #Adding a list of objects
                for inst in value:
                    if(self.manager.identifiersComplete(inst)):
                        ids = self.manager.getInstanceIdentifiers(inst)
                        instPath = self.manager.getTuplePathInObjTree(instanceTuple=tuple([polyObj.className, ids, inst]))
                        if instPath == []:
                            pass
                        elif instPath == None:
                            newBranch = tuple([polyObj.className, ids, inst])
                            self.manager.addNewBranch(traversalList=[], branchTuple=newBranch)
                        else:
                            #add as a duplicate branch
                            duplicateBranchTuple = tuple([polyObj.className, ids, tuple([])]) 
                            self.manager.replaceOriginalTuple(self, originalPath = instPath, newPath=[duplicateBranchTuple], newTuple=duplicateBranchTuple)
            else:
                #Adding one object
                if(self.manager.identifiersComplete(value)):
                    ids = self.manager.getInstanceIdentifiers(value)
                    valuePath = self.manager.getTuplePathInObjTree(instanceTuple=tuple([polyObj.className, ids, value]))
                    if(valuePath == []):
                        #Do nothing, because the branch is already accounted for.
                        pass
                    elif(valuePath == None):
                        #add the new Branch
                        newBranch = tuple([polyObj.className, ids, value])
                        self.manager.addNewBranch(traversalList=[], branchTuple=newBranch)
                    else:
                        #add as a duplicate branch
                        duplicateBranchTuple = tuple([polyObj.className, ids, tuple(valuePath)])
                        self.manager.replaceOriginalTuple(self, originalPath=valuePath, newPath=[duplicateBranchTuple], newTuple=duplicateBranchTuple)

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

BASE_CHARS = tuple("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
BASE_DICT = dict((c, v) for v, c in enumerate(BASE_CHARS))
BASE_LEN = len(BASE_CHARS)

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