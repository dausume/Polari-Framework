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
from polariDBmanagement.managedDB import managedDatabase
from managedDataComms import *
from polariAI.definePolari import *
import unittest

if(__name__=='__main__'):
    namedTestClass = managedDatabase(name='TestDataBase')
    namedTestClass.Path = os.getcwd()
    (namedTestClass).createFile()
    (namedTestClass).makeTableByClass(absDirPath=os.getcwd(),definingFile='definePolari',className='Polari')
    listToStr = ' '.join(map(str, namedTestClass.tables)) 
    print('Tables: [' + listToStr + ']')
    testPolari = Polari(name='testPolari')
    (namedTestClass).saveInstanceInDB(testPolari)
    dataSets = (namedTestClass).getAllInTable('Polari')
    listToStr = ' '.join(map(str, dataSets))
    print('Get all Polari Data Sets: [' + listToStr + ']')
    (namedTestClass).deleteFile()
    unittest.main()
    

class managedDB_testClass(unittest.TestCase):
    #A method which runs once before any tests in the test case.
    @classmethod
    def setUpClass(cls):
        cls.defaultTestClass = managedDatabase()
        cls.namedTestClass = managedDatabase('TestDataBase')
        #(cls.namedTestClass).
        print('Test Case Data is set up.')

    #A method which runs once after all tests in the test case are completed
    @classmethod
    def tearDownClass(cls):
        print('Test Case Data was torn down.')

    def setUp(self):
        print('Setting up before a test is run.')

    def tearDown(self):
        print('Tearing down at the end of the class.')

    def test_singleDefault(self):
        classJSON = getJSONforClass(definingFile='polariDBmanagement.managedDB', className='managedDatabase', passedInstances=self.defaultTestClass )
        print(classJSON)

    def testTableCreation(self):
        (self.namedTestClass).createFile()
        (self.namedTestClass).makeTableByClass(absDirPath=os.getcwd(),definingFile='definePolari.py',className='Polari')
        testPolari = Polari(name='testPolari')
        (self.namedTestClass).saveInstanceInDB(testPolari)
        (self.namedTestClass).getAllInTable('Polari')
        (self.namedTestClass).deleteFile()

    def test_singleNamed(self):
        classJSON = getJSONforClass(definingFile='polariDBmanagement.managedDB', className='managedDatabase', passedInstances=self.namedTestClass )
        print(classJSON)