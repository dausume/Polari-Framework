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
import types, inspect
from functools import wraps # This convenience func preserves name and docstring

#Defines a Decorator @managerObject, which allocates all variables and functions necessary for
#an object to be a the manager object to an Object Tree.
def managerObject(init):
    parameters = inspect.getfullargspec(init)[0]

    @wraps(init)
    def new_init(self, *args):
        if not 'objectTyping' in zip(parameters[1:], args):
            setattr(self, 'objectTyping', [])
        if not 'manager' in zip(parameters[1:], args):
            setattr(self, 'manager', None)
        if not 'objectTree' in zip(parameters[1:], args):
            setattr(self, 'objectTree', None)
        for name, value in zip(parameters[1:], args):
            if(name == 'objectTyping' or name=='manager' or name=='objectTree'):
                setattr(self, name, value)
        new_init = init(self, *args)
        setattr( self, '__setattr__', types.MethodType(__setattr__, self) )
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
        else:
            (polyObj.objectReferencesDict)
        #Throw event indicating that the variable was changed
        #WRITE CODE HERE
        #Assign the variable
        super(setattr, self).__setattr__(name, value)

def makeObjectTree(self):
    print('Added function to tree!!')
    if(self != None):
        print('self passed into function properly!!', self)

class testClass_person:
    @managerObject
    def __init__(self, name, age):
        pass

person = testClass_person("testy", 25)
print(person.name, person.age)