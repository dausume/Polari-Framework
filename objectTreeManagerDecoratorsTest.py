from objectTreeManagerDecorators import *
from objectTreeDecorators import *

class testObj(managerObject):
    @managerObjectInit
    def __init__(self):
        self.testVar = None
        self.name = "abcdef"
        self.objList = []


class secondTestObj(treeObject):
    @treeObjectInit
    def __init__(self):
        self.name = 'name'

def printVariables(obj):
    selfPolyObj = obj.getObject(obj)
    print('--Statement for Object \'' + selfPolyObj.className + '\'--')
    for var in selfPolyObj.polyTypedVars:
        print(var.name + ': ', var.typingDicts)
    print('------------------------------------------')

if(__name__=='__main__'):
    someObj = testObj()
    #print('Printing Object Tree')
    #print(someObj.objectTree)
    secondObj = secondTestObj()
    someObj.objList.append(secondObj)
    #print('Printing Object Tree with added obj')
    #print(someObj.objectTree)
    #printVariables(someObj)
    print('Finished Run')