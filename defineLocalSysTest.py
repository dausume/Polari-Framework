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
from defineLocalSys import *
from managedDataComms import *
import unittest, logging, os

class isoSys_testClass(unittest.TestCase):
    #A method which runs once before any tests in the test case.
    @classmethod
    def setUpClass(cls):
        testLogger = logging.getLogger(__name__)
        testLogger.setLevel(logging.INFO)
        logging.basicConfig(filename='isoSys_LogTest')
        print('Test Case Data is set up.')

    #A method which runs once after all tests in the test case are completed
    @classmethod
    def tearDownClass(cls):
        logging.info('Test Case Data was torn down.')

    def setUp(self):
        self.defaultTestClass = isoSys()
        self.namedTestClass = isoSys('TestFile')
        logging.info('Setting up before a test is run.')

    def tearDown(self):
        logging.info('Tearing down at the end of the class.')

    def test_singleDefault(self):
        classJSON = getJSONforClass(definingFile='defineLocalSys', className='isoSys', passedInstances=self.defaultTestClass )
        logging.info(classJSON)

    def test_singleNamed(self):
        classJSON = getJSONforClass(definingFile='defineLocalSys', className='isoSys', passedInstances=self.namedTestClass)
        logging.info(classJSON)

if(__name__=='__main__'):
    unittest.main()