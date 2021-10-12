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
from managedFolders import managedFolder
from managedFiles import managedFile
from managedExecutables import managedExecutable
from dataChannels import *
from managedApp import *
from defineLocalSys import isoSys
from polariUser import User
import platform

#An auto-named instance of a User's Interfacing and their saved info on pages navigated through with a given application.
class managedUserInterface():
    def __init__(self, hostApp = None, launchMethod='local'):
        #The User that has been recorded utilizing this User Interface
        self.User = None
        #A unique identifier auto generated to ensure data and events flow to the
        #correct locations between systems.
        self.identifier = None
        #The dataChannel which exists on the client-side Interface for localized Apps.
        #For remote applications which operate off of a server, this is only for configuration.
        self.interfaceChannel = None
        #The main application that this User is interfacing with. (Which hosts this UI)
        self.manager = None
        #The System registered as being used to Interface with the Application
        self.accessSystem = None
        #The Browser used by the User to access the application (Chrome, Microsoft Edge, FireFox, etc..)
        self.browserModel = None
        #Tuples of different programming languages used in app and their versions
        self.versioningTuples = []
        #The Page this user is sent to after logging in or when navigating to the landing while login info is active.
        self.HomePage = None
        #The List of Tuples Pages from a single PageSource currently Opened in the Application, and the number of
        #pages from the same source that have been opened. EX: [(HomePage,1),(ManageUsersPage,2),(ManageAccessPage,1)]
        self.browserPages = []
        #Data Streams comprised from the combination of all Page instance data streams.
        self.dataStreams = []
        #The remote events which may occur that affect the client side due to changes on
        #the python-system side, or events that may be triggered on the python-system
        #side due to actions by the user on the client side.
        self.remoteEvents = []
        self.setPolariPythonVersions()
        if(managedApp != None and launchMethod == 'local'):
            self.manager = hostApp
            self.localAppLaunch()

    #def __setattr__(self, key, value):
        #Throw event indicating that the variable was changed
        #WRITE CODE HERE
        #Assign the variable
    #    super(Point, self).__setattr__(key, value)

    def localAppLaunch(self):
        self.HomePage = (self.hostApp).launchPage
        self.interfaceChannel = (self.hostApp).localChannel
        self.addPageInstance(self.HomePage)

    def addPageInstance(self, sourcePage):
        newPageInstance = pageInstance(sourcePage=sourcePage)
        (self.browserPages).append(pageInstance)

    def setPolariPythonVersions(self):
        if(self.versioningTuples == []):
            self.versioningTuples.append(tuple(['polari','0.0.0']))
            self.versioningTuples.append(tuple(['python', platform.python_version()]))

    #Makes a basic UI with no User attached by launching the anonymous login Landing Page
    #No name is given, since anonymous users are not meant to be saved to the Database.
    def makeAnonymousUI(self, landingPage, supportFiles):
        self.accessSystemActive = isoSys(name='localSys')
        self.HomePage = browserSourcePage(mainPage=landingPage, supportFiles=supportFiles)
        self.browserPages.append(self.HomePage)

class pageInstance():
    def __init__(self, UserInterface=None, sourcePage = None):
        #The user inteface this page instance was created for and hosted on.
        self.manager = UserInterface
        self.identifier = None
        self.sourcePage = sourcePage
        #Data Streams which this page should be expecting to come into it's app.
        self.dataStreams = []
        #The remote events which may occur that affect the page due to changes on
        #the python-system side, or events that may be triggered on the python-system
        #side due to actions by the user on the page.
        self.remoteEvents = []

    #def __setattr__(self, key, value):
        #Throw event indicating that the variable was changed
        #WRITE CODE HERE
        #Assign the variable
    #    super(Point, self).__setattr__(key, value)



    #def __setattr__(self, key, value):
        #Throw event indicating that the variable was changed
        #WRITE CODE HERE
        #Assign the variable
    #    super(Point, self).__setattr__(key, value)
        