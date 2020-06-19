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
import unittest, os, sys, webbrowser
from defineLocalSys import *
from managedDataComms import *
from managedExecutables import *
from definePolari import *
from managedApp import *
from managedFolders import *

def OpenInterface():
    #Runs the case where the Polari Systems are running for the first time.
    if(not os.path.exists('sysMain.db')):
        #Create the main Polari, which manages the operations on the local system.
        #This main Polari effectively claims the polari core folder as it's folder.
        systemsMainPolari = Polari(name='sysMain', displayName='Local System Main Polari', filePath=os.path.dirname(os.path.abspath(__file__)))
        #Then, build a tree that accounts for all folders within the polari Core folder.
        systemsMainPolari.buildTree()
        #Get all .db files in the folder tree.
        #These can later be used to establish the sub-apps and sub-polari within the
        #system under the main Polari.
        databaseFileInstances = systemsMainPolari.getFilesInTree(extensions=['db'])
        #Go through each .db and check if the managedDatabase for a given App or Polari
        #within the database matches itself.  If it does, generate that object based
        #on the information within that database and add it as a subordinate of the main
        #Note: All Polari and Apps that exist locally should be subordinate to the main.
        #WRITE CODE FOR APPENDING SUBORDINATE OBJECTS HERE
        #Create an application meant for managing the Polari and Applications.
        PolariManagerApp = managedApp(name='polariManager', displayName='Polari & Applications Manager', filePath=os.path.dirname(os.path.abspath(__file__)) + '/polariManager')
        #Generate the database for the Polari and it's management application.
        #Since the Folder housing the main polari will not match it's name, we create
        #the object and file in the file system using __init__ and createFile.  Whereas
        #the Polari Manager App should be allowed to have it's db and folder name match,
        #so we just use createDatabase().
        systemsMainPolari.DB = managedDatabase(name='sysMain', manager=systemsMainPolari)
        (systemsMainPolari.DB).createFile()
        (PolariManagerApp.DB).createDatabase()
        #Set up the main-local data channel for the local Management app
        #and the local data channel for the System Main Polari.
        systemsMainPolari.localChannel = dataChannel(name='sysMain_locDC')
        PolariManagerApp.localChannel = dataChannel(name='polariManager_locDC')
        #Use the already existing template (which should be downloaded as part of the
        #base functionality) to generate a Polari Application for Managing and creating
        #basic Polari and Polari based Applications, using folders with pre-existing
        #source code.
        launchPage = browserSourcePage(name='PolariLanding')
        #Creating only the launch page of the App for now...
        launchPage.originPage = managedFile(name='PolariLanding.html')
        (launchPage.originPage).Path = os.path.dirname(os.path.abspath(__file__)) + '/polariManager/PolariLanding'
        launchPage.localSysJS = managedFile(name='PolariLanding.js')
        (launchPage.localSysJS).Path = os.path.dirname(os.path.abspath(__file__)) + '/polariManager/PolariLanding'
        launchPage.stylePage = managedFile(name='PolariLanding.css')
        (launchPage.stylePage).Path = os.path.dirname(os.path.abspath(__file__)) + '/polariManager/PolariLanding'
        launchPage.pageChannel = dataChannel(name='PolariLanding.json')
        (launchPage.pageChannel).Path = os.path.dirname(os.path.abspath(__file__)) + '/polariManager/PolariLanding'
        #Add the launch sourcepage instance to the Management App.
        PolariManagerApp.addLaunchPage(launchPage)
        #Generate a Local User Interface (An electron browser instance)
        #Have it pull the data from the template Application for launch,
        #and then if there is User data (there won't be the first time)
        #then that user data is pulled in and may alter page data and configuration.
        localUserInterface = managedUI()
        localUserInterface.browserModel = 'Electron'
        localUserInterface.addPageInstance(PolariManagerApp.landingSourcePage)
        localUserInterface.HomePage = PolariManagerApp.landingSourcePage
    #If it does already exist, load it.
    else:
        mainPolari = Polari(name='sysMain')
        mainPolari.polariLoad(os.path.dirname(os.path.abspath(__file__)))
        

print('Made it into the file!')