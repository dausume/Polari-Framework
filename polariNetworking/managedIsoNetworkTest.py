import logging
from polariNetworking.managedIsoNetwork import managedIsoNetwork
import unittest

class managedIsoNetwork_testClass(unittest.TestCase):
    #A method which runs once before any tests in the test case.
    @classmethod
    def setUpClass(cls):
        logging.basicConfig(filename='image_LogTest')
        testLogger = logging.getLogger(name='image_testLogger')
        testLogger.setLevel(logging.INFO)
        print('Test Case Data is set up.')

    #A method which runs once after all tests in the test case are completed
    @classmethod
    def tearDownClass(cls):
        logging.info('Test Case Data was torn down.')

    def setUp(self):
        self.testClassInstance = managedIsoNetwork(name='testLAN')
        logging.info('Setting up before a test is run.')

    def tearDown(self):
        logging.info('Tearing down at the end of the class.')

    def test_getHostNameOnLAN(self):
        self.testClassInstance.getHostsOnCurrentWifi()
        #Should be at least one since it needs to pick up self as host as well.
        print("List of hostNames on Local Network: ", self.testClassInstance.hostNames)
        self.assertTrue(len(self.testClassInstance.hostNames) > 0, "Failed to detect self or any other hosts on LAN or wifi, make sure other host exists for this test.")

    def test_checkNetworkInterfaces(self):
        self.testClassInstance.getNetworkInterfaces()

if(__name__=='__main__'):
    unittest.main()