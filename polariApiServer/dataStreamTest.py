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
import unittest, logging, os

if(__name__=='__main__'):
    localSys = isoSys(name='localSys')
    print('Made isoSys')
    fakeManager = testObj()
    print('made test object / manager')
    secondObj = secondTestObj()
    print('made secondary test object')
    fakeManager.objList.append(secondObj)
    print('added secondary test object to manager\'s object list.')
    fakeServer = polariServer(name='testServer', displayName='displayName', hostSystem=localSys, manager=fakeManager)
    print('Created polariServer with a set manager.')
    fakeServer.startupPolariServer()
    print('Finished setting up server for manager object.')

#First, set up a fake app.
#Second, set up a fake local datastream for that app.
#Third, make some fake Users and input them into the App as active users.
#Fourth, make a data stream that sends all of the fake App's Users whenever updated.
#Fifth, confirm that the data was properly entered.
#Sixth, emulate a client side application requesting only the username variable.
#sevent, 
class dataStream_testClass(unittest.TestCase):
    #A method which runs once before any tests in the test case.
    @classmethod
    def setUpClass(cls):
        logging.basicConfig(filename='dataStream_LogTest')
        testLogger = logging.getLogger(name='dataStream_testLogger')
        testLogger.setLevel(logging.INFO)
        print('Test Case Data is set up.')

    #A method which runs once after all tests in the test case are completed
    @classmethod
    def tearDownClass(cls):
        logging.info('Test Case Data was torn down.')

    def setUp(self):
        self.fakeApp = managedApp()
        self.defaultTestClass = dataStream()
        self.namedTestClass = dataStream('TestFile')
        logging.info('Setting up before a test is run.')

    def tearDown(self):
        logging.info('Tearing down at the end of the class.')

    def test_singleDefault(self):
        classJSON = getJSONforClass(definingFile='managedDataComms', className='dataChannel', passedInstances=self.defaultTestClass )
        logging.info(classJSON)

    def test_singleNamed(self):
        classJSON = getJSONforClass(definingFile='managedDataComms', className='dataChannel', passedInstances=self.namedTestClass)
        logging.info(classJSON)