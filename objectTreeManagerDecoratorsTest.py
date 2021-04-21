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
        #self.var_list = []
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
        self.var_TextIOWrapper.close()
        #Create one variable for every ignored object type defined, to ensure they can be set properly.
        self.obj_struct_time = time.localtime(time.time())
        self.obj_API = falcon.API()
        self.obj_polariList = []
        #Create samples of attaching objects to the manager in both single and list format cases, with initial null and empty 
        self.someObj_initFilled = testTreeObj(manager=self)
        self.objList_initFilled = [testTreeObj(manager=self), testTreeObj(manager=self)]
        self.someObj_postFill = None
        self.objList_postFillList = []

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
        #self.var_list = []
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
        self.var_TextIOWrapper.close()
        #Create one variable for every ignored object type defined, to ensure they can be set properly.
        self.obj_struct_time = time.localtime(time.time())
        self.obj_API = falcon.API()
        self.obj_polariList = []
        #Create samples of attaching objects to the manager in both single and list format cases, with initial null and empty 
        self.someObj_initFilled = testTreeBranchObj(manager=self.manager)
        self.objList_initFilled = [testTreeBranchObj(manager=self.manager), testTreeBranchObj(manager=self.manager)]
        self.someObj_postFill = None
        self.objList_postFillList = []

class testTreeBranchObj(treeObject):
    @treeObjectInit
    def __init__(self):
        pass

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
        print(' - Test Case Data is set up - ')

    #A method which runs once after all tests in the test case are completed
    @classmethod
    def tearDownClass(cls):
        print(' - Test Case Data was torn down - ')

    def setUp(self):
        self.mngObj = testManagerObj()
        print('Setting up before a test is run.')

    def tearDown(self):
        self.mngObj.var_TextIOWrapper.close()
        print(self.mngObj.objectTree)
        #print('----- List of PolyTyped Objects -----')
        #print(self.mngObj.getListOfClassInstances(className='polyTypedObject'))
        print('----- List of Test Manager Objects ------')
        print(self.mngObj.getListOfClassInstances(className='testManagerObj'))
        print('----- List of Test Tree Objects ------')
        print(self.mngObj.getListOfClassInstances(className='testTreeObj'))
        print('----- List of Test Tree Branch Objects ------')
        print(self.mngObj.getListOfClassInstances(className='testTreeBranchObj'))
        print('----- List of Objects at Depth 0 in Tree ------')
        print(self.mngObj.getListOfInstancesAtDepth(target_depth=0))
        print('----- List of Objects at Depth 1 in Tree ------')
        print(self.mngObj.getListOfInstancesAtDepth(target_depth=1))
        print('----- List of Objects at Depth 2 in Tree ------')
        print(self.mngObj.getListOfInstancesAtDepth(target_depth=2))
        print('Tearing down at the end of the object tree test case.')

    #Tests that all standard variable types can be set and supported on a manager object.
    def test_allStandardTypesOnManager(self):
        missingStandardTypes = []
        wrongStandardTypes = []
        missingIgnoredObjects = []
        wrongIgnoredTypes = []
        for someType in standardTypesPython:
            #Dis-regard list because it is replaced by ignored custom type polariList on manager
            #and tree objects.
            if(someType != 'list'):
                if(hasattr(self.mngObj, 'var_' + someType)):
                    someVar = getattr(self.mngObj, 'var_'+someType)
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
        #List is going to be missing because it is overwritten by polariList
        self.assertEqual(len(missingStandardTypes), 0)
        
    #Tests that all standard variable types can be set and supported on a tree object.
    def test_allStandardTypesOnTreeObj(self):
        missingStandardTypes = []
        wrongStandardTypes = []
        missingIgnoredObjects = []
        wrongIgnoredTypes = []
        for someType in standardTypesPython:
            #Dis-regard list because it is replaced by ignored custom type polariList on manager
            #and tree objects.
            if(someType != 'list'):
                if(hasattr(self.mngObj.someObj_initFilled,'var_' + someType)):
                    someVar = getattr(self.mngObj.someObj_initFilled, 'var_'+someType)
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
        for someType in ignoredObjectsPython:
            if(hasattr(self.mngObj,'obj_' + someType)):
                someVar = getattr(self.mngObj, 'obj_'+someType)
                if(type(someVar).__name__ == someType):
                    pass
                else:
                    wrongIgnoredObjects.append('\"Expected Type: '+ someType + ' in variable obj_' + someType + ', Found Type: ' + type(someVar).__name__ + '\"')
            else:
                missingIgnoredObjects.append('\"Expected obj_' + someType + ' with a value of type ' + someType +' in the treeObject, but variable did not exist\"')
        if(len(wrongIgnoredObjects) != 0):
            print('Wrong Standard Types: ', wrongIgnoredObjects)
        elif(len(missingIgnoredObjects) != 0):
            print('Missing Standard Types: ', missingIgnoredObjects)
        self.assertEqual(len(wrongIgnoredObjects), 0)
        self.assertEqual(len(missingIgnoredObjects), 0)

    def test_ignoredObjectsOnTreeObject(self):
        missingIgnoredObjects = []
        wrongIgnoredObjects = []
        for someType in ignoredObjectsPython:
            if(hasattr(self.mngObj.someObj_initFilled,'obj_' + someType)):
                someVar = getattr(self.mngObj.someObj_initFilled, 'obj_'+someType)
                if(type(someVar).__name__ == someType):
                    pass
                else:
                    wrongIgnoredObjects.append('\"Expected Type: '+ someType + ' in variable obj_' + someType + ', Found Type: ' + type(someVar).__name__ + '\"')
            else:
                missingIgnoredObjects.append('\"Expected obj_' + someType + ' with a value of type ' + someType +' in the treeObject, but variable did not exist\"')
        if(len(wrongIgnoredObjects) != 0):
            print('Wrong Standard Types: ', wrongIgnoredObjects)
        elif(len(missingIgnoredObjects) != 0):
            print('Missing Standard Types: ', missingIgnoredObjects)
        self.assertEqual(len(wrongIgnoredObjects), 0)
        self.assertEqual(len(missingIgnoredObjects), 0)

    def test_initFilledTreeObjectsOnManager(self):
        #Check to make sure an object typing has been generated for both the manager and the treeObject
        self.assertIsNotNone(self.mngObj.getObjectTyping(className='testManagerObj'))
        self.assertIsNotNone(self.mngObj.getObjectTyping(className='testTreeObj'))
        #Check that the values were populated properly
        self.assertIsInstance(self.mngObj, testManagerObj, msg="Asserts the manager obect is an instance of the test manager object.")
        self.assertIsInstance(self.mngObj.someObj_initFilled, testTreeObj, msg = "Single tree object set to var on manager at initiation should be a testTreeObj Instance.")
        self.assertIsInstance(self.mngObj.objList_initFilled[0], testTreeObj, msg = "The first tree object set on a list var on manager at initiation should be a testTreeObj Instance.")
        self.assertIsInstance(self.mngObj.objList_initFilled[1], testTreeObj, msg = "The second tree object set on a list var on manager at initiation should be a testTreeObj Instance.")
        #Check that the values/objects were properly allocated onto the tree.
        #The manager's path should always be an empty list since it is the base.
        #The treeObject path, so long as it returns not None meaning a value was found, is good.
        mngPath = self.mngObj.getTuplePathInObjTree(self.mngObj.getInstanceTuple(self.mngObj))
        singleTreeObjPath = self.mngObj.getTuplePathInObjTree(self.mngObj.getInstanceTuple(self.mngObj.someObj_initFilled))
        listTreeObjOnePath = self.mngObj.getTuplePathInObjTree(self.mngObj.getInstanceTuple(self.mngObj))
        listTreeObjTwoPath = self.mngObj.getTuplePathInObjTree(self.mngObj.getInstanceTuple(self.mngObj))
        #Asserts the manager is at the base.
        self.assertEqual(len(mngPath), 1, msg="The manager object itself should be at the base of it\'s object tree.")
        #Asserts the treeObject should be inside the tree.
        self.assertIsNotNone(singleTreeObjPath, msg="Single tree object set to var on manager at initiation should be in the object tree.")
        self.assertIsNotNone(listTreeObjOnePath, msg="The first tree object set on a list var on manager at initiation should be in the object tree.")
        self.assertIsNotNone(listTreeObjTwoPath, msg="The second tree object set on a list var on manager at initiation should be in the object tree.")

    def test_postFilledTreeObjectsOnManager(self):
        #Check to make sure an object typing has been generated for both the manager and the treeObject
        self.assertIsNotNone(self.mngObj.getObjectTyping(className='testManagerObj'))
        self.assertIsNotNone(self.mngObj.getObjectTyping(className='testTreeObj'))
        #Set the values on the manager object.
        self.mngObj.someObj_postFill = testTreeObj(manager=self.mngObj)
        self.mngObj.objList_postFillList.append(testTreeObj(manager=self.mngObj))
        self.mngObj.objList_postFillList.append(testTreeObj(manager=self.mngObj))
        #Check that the values were populated properly
        self.assertIsInstance(self.mngObj, testManagerObj, msg="Asserts the manager obect is an instance of the test manager object.")
        self.assertIsInstance(self.mngObj.someObj_postFill, testTreeObj, msg = "Single tree object set to var on manager after initiation should be a testTreeObj Instance.")
        self.assertIsInstance(self.mngObj.objList_postFillList[0], testTreeObj, msg = "The first tree object set on a list var on manager after initiation should be a testTreeObj Instance.")
        self.assertIsInstance(self.mngObj.objList_postFillList[1], testTreeObj, msg = "The second tree object set on a list var on manager after initiation should be a testTreeObj Instance.")
        #Check that the values/objects were properly allocated onto the tree.
        #The manager's path should always be an empty list since it is the base.
        #The treeObject path, so long as it returns not None meaning a value was found, is good.
        mngPath = self.mngObj.getTuplePathInObjTree(self.mngObj.getInstanceTuple(self.mngObj))
        singleTreeObjPath = self.mngObj.getTuplePathInObjTree(self.mngObj.getInstanceTuple(self.mngObj.someObj_postFill))
        listTreeObjOnePath = self.mngObj.getTuplePathInObjTree(self.mngObj.getInstanceTuple(self.mngObj.objList_postFillList[0]))
        listTreeObjTwoPath = self.mngObj.getTuplePathInObjTree(self.mngObj.getInstanceTuple(self.mngObj.objList_postFillList[1]))
        #Asserts the manager is at the base.
        self.assertEqual(len(mngPath), 1, msg="The manager object itself should be at the base of it\'s object tree.")
        #Asserts the treeObject should be inside the tree.
        self.assertIsNotNone(singleTreeObjPath, msg="Single tree object set to var on manager after initiation should be in the object tree.")
        self.assertIsNotNone(listTreeObjOnePath, msg="The first tree object set on a list var on manager after initiation should be in the object tree.")
        self.assertIsNotNone(listTreeObjTwoPath, msg="The second tree object set on a list var on manager after initiation should be in the object tree.")

    def test_postFilledTreeObjectsOnTreeObject(self):
        #Check to make sure an object typing has been generated for both the manager and the treeObject
        self.assertIsNotNone(self.mngObj.getObjectTyping(className='testManagerObj'))
        self.assertIsNotNone(self.mngObj.getObjectTyping(className='testTreeObj'))
        #Check that the dependency values were populated properly
        self.assertIsInstance(self.mngObj, testManagerObj, msg="Asserts the manager obect is an instance of the test manager object.")
        self.assertIsInstance(self.mngObj.someObj_initFilled, testTreeObj, msg="Asserts the value someObj_initFilled on manager obect is an instance of the test tree object.")
        #Set the values on the single variable treeObject on manager at initiation.
        self.mngObj.someObj_initFilled.someObj_postFill = testTreeBranchObj(manager=self.mngObj)
        self.mngObj.someObj_initFilled.objList_postFillList.append(testTreeBranchObj(manager=self.mngObj))
        self.mngObj.someObj_initFilled.objList_postFillList.append(testTreeBranchObj(manager=self.mngObj))
        #Check that the values were populated properly
        self.assertIsInstance(self.mngObj.someObj_initFilled.someObj_postFill, testTreeBranchObj, msg = "Assert the values are set to be testTreeBranchObj type.")
        self.assertIsInstance(self.mngObj.someObj_initFilled.objList_postFillList[0], testTreeBranchObj, msg = "Assert the values are initially set to be testTreeBranchObj type.")
        #Check that the values/objects were properly allocated onto the tree.
        #The manager's path should always be an empty list since it is the base.
        #The treeObject path, so long as it returns not None meaning a value was found, is good.
        mngPath = self.mngObj.getTuplePathInObjTree(self.mngObj.getInstanceTuple(self.mngObj))
        treeObjPath = self.mngObj.getTuplePathInObjTree(self.mngObj.getInstanceTuple(self.mngObj.someObj_initFilled.someObj_postFill))
        listTreeObjOnePath = self.mngObj.getTuplePathInObjTree(self.mngObj.getInstanceTuple(self.mngObj.someObj_initFilled.objList_postFillList[0]))
        listTreeObjTwoPath = self.mngObj.getTuplePathInObjTree(self.mngObj.getInstanceTuple(self.mngObj.someObj_initFilled.objList_postFillList[1]))
        #Asserts the manager is at the base.
        self.assertEqual(len(mngPath), 1, msg="The manager object itself should be at the base of it\'s object tree.")
        #Asserts the treeObject should be inside the tree.
        self.assertIsNotNone(treeObjPath, msg="Single tree object set to var on a tree object after initiation should be in the object tree.")
        #Asserts the treeObject assigned at initiation in a list is in the tree.
        self.assertIsNotNone(listTreeObjOnePath, msg="The first tree object set on a list var on a tree object after initiation should be in the object tree.")
        self.assertIsNotNone(listTreeObjTwoPath, msg="The second tree object set on a list var on a tree object after initiation should be in the object tree.")

    def test_initFilledTreeObjectsOnTreeObject(self):
        #Check to make sure an object typing has been generated for both the manager and the treeObject
        self.assertIsNotNone(self.mngObj.getObjectTyping(className='testManagerObj'))
        self.assertIsNotNone(self.mngObj.getObjectTyping(className='testTreeObj'))
        #Check that the values were populated properly
        self.assertIsInstance(self.mngObj, testManagerObj, msg="Asserts the manager obect is an instance of the test manager object.")
        self.assertIsInstance(self.mngObj.someObj_initFilled.someObj_initFilled, testTreeBranchObj, msg = "Assert the values are initially set to be treeObjects.")
        self.assertIsInstance(self.mngObj.someObj_initFilled.objList_initFilled[0], testTreeBranchObj, msg = "Assert the values are initially set to be treeObjects.")
        #Check that the values/objects were properly allocated onto the tree.
        #The manager's path should always be an empty list since it is the base.
        #The treeObject path, so long as it returns not None meaning a value was found, is good.
        mngPath = self.mngObj.getTuplePathInObjTree(self.mngObj.getInstanceTuple(self.mngObj))
        treeObjPath = self.mngObj.getTuplePathInObjTree(self.mngObj.getInstanceTuple(self.mngObj.someObj_initFilled.someObj_initFilled))
        listTreeObjOnePath = self.mngObj.getTuplePathInObjTree(self.mngObj.getInstanceTuple(self.mngObj.someObj_initFilled.objList_initFilled[0]))
        listTreeObjTwoPath = self.mngObj.getTuplePathInObjTree(self.mngObj.getInstanceTuple(self.mngObj.someObj_initFilled.objList_initFilled[1]))
        #Asserts the manager is at the base.
        self.assertEqual(len(mngPath), 1, msg="The manager object itself should be at the base of it\'s object tree.")
        #Asserts the treeObject should be inside the tree.
        self.assertIsNotNone(treeObjPath, msg="Single tree object set to var on a tree object at it\'s initiation should be in the object tree.")
        #Asserts the treeObject assigned at initiation in a list is in the tree.
        self.assertIsNotNone(listTreeObjOnePath, msg="The first tree object set on a list var on a tree object at it's initiation should be in the object tree.")
        self.assertIsNotNone(listTreeObjTwoPath, msg="The second tree object set on a list var on a tree object at it's initiation should be in the object tree.")

        
if(__name__=='__main__'):
    unittest.main()
    print('Finished Run')