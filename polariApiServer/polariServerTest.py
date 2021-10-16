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
from polariFiles.dataChannels import *
from polariApiServer.dataStreams import *
from objectTreeManagerDecorators import *
from objectTreeDecorators import *
from polariApiServer.polariServer import *
from polariNetworking.defineLocalSys import *
from objectTreeManagerDecoratorsTest import *
import unittest, logging, os, functools

class polariServer_TestCase(unittest.TestCase):
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
        self.mngObj = testManagerObj(hasServer=True)
        print('Setting up before a test is run.')

    def tearDown(self):
        self.mngObj.var_TextIOWrapper.close()
        print(self.mngObj.objectTree)

    def test_polariServerIsSetOnTree(self):
        #Assert the polariServer typing object exists.
        self.assertIsNotNone(self.mngObj.getObjectTyping(className='polariServer'))
        #Check that the values were populated properly
        print("Manager object: ", self.mngObj)
        print("polServer value: ", self.mngObj.polServer)
        self.assertIsInstance(self.mngObj.polServer, polariServer, msg="Asserts the polServer variable on the manager is populated with a polari server.")
        #Check that the values/objects were properly allocated onto the tree.
        serverPath = self.mngObj.getTuplePathInObjTree(self.mngObj.getInstanceTuple(self.mngObj.polServer))
        #Asserts the treeObject should be inside the tree.
        self.assertIsNotNone(serverPath, msg="Single polariServer as a tree object set to var on manager object at it\'s initiation should be in the object tree.")
        serversList = self.mngObj.getListOfClassInstances(className="polariServer")
        print("List of server objects in manager's tree: ", serversList)
        crudObjectList = self.mngObj.getListOfClassInstances(className="polariCRUD")
        print("List of CRUD objects in manager's tree: ", crudObjectList)
        customApiObjectsList = self.mngObj.getListOfClassInstances(className="polariAPI")
        print("List of custom API objects in manager's tree: ", customApiObjectsList)

    def test_pingBaseAPIs(self):
        print('Pinging the Falcon APIs...')

if(__name__=='__main__'):
    unittest.main()
    print('---- Finished Polari Server Test ----')
    