from objectTreeManagerDecorators import managerObject
import polariApiServer.polariServer
import polariAPI
import unittest

class polariAPI_TestCase(unittest.TestCase):
    #A method which runs once before any tests in the test case.
    @classmethod
    def setUpClass(cls):
        self.mngObj = managerObject(hasServer=True)
        print(' - Test Case Data is set up - ')

    #A method which runs once after all tests in the test case are completed
    @classmethod
    def tearDownClass(cls):
        print(' - Test Case Data was torn down - ')

    def setUp(self):
        print('Setting up before a test is run.')

    def tearDown(self):
        print("Tearing down test...")

if(__name__=='__main__'):
    unittest.main()
    print('-- Finished Generalized Manager Object Test Cases --')