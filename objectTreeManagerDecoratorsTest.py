from objectTreeManagerDecorators import *
from objectTreeDecorators import *
import unittest, logging, os, time, falcon

class testManagerObj(managerObject):
    @managerObjectInit
    def __init__(self):
        #Create one variable for every standard dataType in python, to test and ensure each of them can be set properly.
        self.var_str = ''
        self.var_int = 1
        self.var_float = 0.1
        self.var_complex = complex(1,1)
        self.var_list = []
        self.var_tuple = ()
        self.var_range = range(0,1)
        self.var_dict = {"key":"value"}
        self.var_set = set([1, 2, 3])
        self.var_frozenset = frozenset(['a', 'b', 'c'])
        self.var_bool = True
        self.var_bytes = bytes(1)
        self.var_bytearray = bytearray(b'bytearray')
        self.var_memoryview = memoryview(b'viewBytesMemoryView')
        self.var_type = type('str')
        self.var_NoneType = None
        self.var_TextIOWrapper = open("testDocOne.txt","w+")
        #Create one variable for every ignored object type defined, to ensure they can be set properly.
        self.obj_struct_time = time.localtime(time.time())
        self.obj_API = falcon.API()
        #Create samples of attaching objects to the manager in both single and list format cases, with initial null and empty 
        self.someObj_initFilled = testTreeObj(manager=self)
        self.objList_initFilled = [testTreeObj(manager=self), testTreeObj(manager=self)]
        self.someObj_initNull = None
        self.objList_initEmptyList = []

#standardTypesPython = ['str','int','float','complex','list','tuple','range','dict',
#'set','frozenset','bool','bytes','bytearray','memoryview', 'struct_time', 'type', 'NoneType', 'TextIOWrapper']
#ignoredObjectsPython = ['API']
#dataTypesPython = standardTypesPython + ignoredObjectsPython
class testTreeObj(treeObject):
    @treeObjectInit
    def __init__(self):
        #Create one variable for every standard dataType in python, to test and ensure each of them can be set properly.
        self.var_str = ''
        self.var_int = 1
        self.var_float = 0.1
        self.var_complex = complex(1,1)
        self.var_list = []
        self.var_tuple = ()
        self.var_range = range(0,1)
        self.var_dict = {"key":"value"}
        self.var_set = set([1, 2, 3])
        self.var_frozenset = frozenset(['a', 'b', 'c'])
        self.var_bool = True
        self.var_bytes = bytes(1)
        self.var_bytearray = bytearray(b'bytearray')
        self.var_memoryview = memoryview(b'viewBytesMemoryView')
        self.var_type = type('str')
        self.var_NoneType = None
        self.var_TextIOWrapper = open("testDocOne.txt","w+")
        #Create one variable for every ignored object type defined, to ensure they can be set properly.
        self.obj_struct_time = time.localtime(time.time())
        self.obj_API = falcon.API()
        #Create samples of attaching objects to the manager in both single and list format cases, with initial null and empty 
        self.someObj_initFilled = testTreeObj(manager=self)
        self.objList_initFilledList = [testTreeObj(manager=self), testTreeObj(manager=self)]
        self.someObj_postFilled = None
        self.objList_postFilledList = []

def printVariables(obj):
    selfPolyObj = obj.getObject(obj)
    print('--Statement for Object \'' + selfPolyObj.className + '\'--')
    for var in selfPolyObj.polyTypedVars:
        print(var.name + ': ', var.typingDicts)
    print('------------------------------------------')

class objectTree_TestCase(unittest.TestCase):
    #A method which runs once before any tests in the test case.
    @classmethod
    def setUpClass(cls):
        #testLogger = logging.Logger(name='objectTree_testLogger', level=logging.INFO)
        #logging.basicConfig(filename='objectTree_LogTest')
        print('Test Case Data is set up.')

    #A method which runs once after all tests in the test case are completed
    @classmethod
    def tearDownClass(cls):
        logging.info('Test Case Data was torn down.')

    def setUp(self):
        self.someObj = testManagerObj()
        self.secondObj = testTreeObj(manager=self.someObj)
        print('Setting up before a test is run.')

    def tearDown(self):
        self.someObj.var_TextIOWrapper.close()
        self.secondObj.var_TextIOWrapper.close()
        print('Tearing down at the end of the object tree test case.')

    #Tests that all standard variable types can be set and supported on a manager object.
    def test_allStandardTypesOnManager(self):
        missingStandardTypes = []
        wrongStandardTypes = []
        missingIgnoredObjects = []
        wrongIgnoredTypes = []
        for someType in standardTypesPython:
            if(hasattr(self.someObj, 'var_' + someType)):
                someVar = getattr(self.someObj, 'var_'+someType)
                if(type(someVar).__name__ == someType):
                    pass
                else:
                    wrongStandardTypes.append('\"Expected Type: '+ someType + ' in variable var_' + someType + ', Found Type: ' + type(someVar).__name__ + '\"')
            else:
                missingStandardTypes.append('\"Expected var_' + someType + ' with a value of type ' + someType +' in manager, but variable did not exist\"')
        if(len(wrongStandardTypes) != 0):
            print('Wrong Standard Types: ', wrongStandardTypes)
        elif(len(missingStandardTypes) != 0):
            print('Missing Standard Types: ', missingStandardTypes)
        self.assertEqual(len(wrongStandardTypes), 0)
        self.assertEqual(len(missingStandardTypes), 0)
        
    #Tests that all standard variable types can be set and supported on a tree object.
    def test_allStandardTypesOnTreeObj(self):
        missingStandardTypes = []
        wrongStandardTypes = []
        missingIgnoredObjects = []
        wrongIgnoredTypes = []
        for someType in standardTypesPython:
            if(hasattr(self.secondObj,'var_' + someType)):
                someVar = getattr(self.secondObj, 'var_'+someType)
                if(type(someVar).__name__ == someType):
                    pass
                else:
                    wrongStandardTypes.append('\"Expected Type: '+ someType + ' in variable var_' + someType + ', Found Type: ' + type(someVar).__name__ + '\"')
            else:
                missingStandardTypes.append('\"Expected var_' + someType + ' with a value of type ' + someType +' in the treeObject, but variable did not exist\"')
        if(len(wrongStandardTypes) != 0):
            print('Wrong Standard Types: ', wrongStandardTypes)
        elif(len(missingStandardTypes) != 0):
            print('Missing Standard Types: ', missingStandardTypes)
        self.assertEqual(len(wrongStandardTypes), 0)
        self.assertEqual(len(missingStandardTypes), 0)

    def test_ignoredObjectsOnManager(self):
        missingIgnoredObjects = []
        wrongIgnoredObjects = []
        for someType in standardTypesPython:
            if(hasattr(self.someObj,'var_' + someType)):
                someVar = getattr(self.someObj, 'var_'+someType)
                if(type(someVar).__name__ == someType):
                    pass
                else:
                    wrongIgnoredObjects.append('\"Expected Type: '+ someType + ' in variable var_' + someType + ', Found Type: ' + type(someVar).__name__ + '\"')
            else:
                missingIgnoredObjects.append('\"Expected var_' + someType + ' with a value of type ' + someType +' in the treeObject, but variable did not exist\"')
        if(len(wrongIgnoredObjects) != 0):
            print('Wrong Standard Types: ', wrongIgnoredObjects)
        elif(len(missingIgnoredObjects) != 0):
            print('Missing Standard Types: ', missingIgnoredObjects)
        self.assertEqual(len(wrongIgnoredObjects), 0)
        self.assertEqual(len(missingIgnoredObjects), 0)

    def test_ignoredObjectsOnTreeObject(self):
        missingIgnoredObjects = []
        wrongIgnoredObjects = []
        for someType in standardTypesPython:
            if(hasattr(self.secondObj,'var_' + someType)):
                someVar = getattr(self.secondObj, 'var_'+someType)
                if(type(someVar).__name__ == someType):
                    pass
                else:
                    wrongIgnoredObjects.append('\"Expected Type: '+ someType + ' in variable var_' + someType + ', Found Type: ' + type(someVar).__name__ + '\"')
            else:
                missingIgnoredObjects.append('\"Expected var_' + someType + ' with a value of type ' + someType +' in the treeObject, but variable did not exist\"')
        if(len(wrongIgnoredObjects) != 0):
            print('Wrong Standard Types: ', wrongIgnoredObjects)
        elif(len(missingIgnoredObjects) != 0):
            print('Missing Standard Types: ', missingIgnoredObjects)
        self.assertEqual(len(wrongIgnoredObjects), 0)
        self.assertEqual(len(missingIgnoredObjects), 0)

    def test_initFilledTreeObjectsOnManager(self):
        #Check that the values were populated properly
        self.someObj_initFilled
        self.objList_initFilled
        #Check that the values/objects were properly allocated onto the tree.
        self.someObj_initFilled
        self.objList_initFilled

    def test_initFilledTreeObjectsOnManager(self):
        #Check that the values were populate properly when assigned.
        self.someObj_initFilled
        self.objList_initFilled
        #Check that the values/objects were properly allocated onto the tree after being assigned.
        self.someObj_initFilled
        self.objList_initFilled

        

if(__name__=='__main__'):
    #someObj = testManagerObj()
    #print('Printing Object Tree')
    #print(someObj.objectTree)
    #secondObj = testTreeObj(manager=someObj)
    #someObj.objList_initEmptyList.append(secondObj)
    #print('Printing Object Tree with added obj')
    #print(someObj.objectTree)
    #printVariables(someObj)
    unittest.main()
    print('Finished Run')