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
from dataChannels import *
from dataStreams import *
from objectTreeManagerDecorators import *
from objectTreeDecorators import *
from polariServer import *
from defineLocalSys import *
from objectTreeManagerDecoratorsTest import *
import unittest, logging, os, functools
#class parentCls:
#    def __init__(self, *args, **keywordargs):
#        print("In parent init..")
#        #functools.update_wrapper(self.__class__, obj)

#    def __setattr__(self, name, value):
#        print("inherited setattr")
#
#    def __getattribute__(self, name):
#        print("inhereted getattr")
#
#class someClass(parentCls):
#    
#    def __init__(self):
#        self.varZero = "val0"
#        self.varOne = None
#
#    def __setattr__(self, name, value):
#        print("overwritten setattr printing value")
#        #super(self.__class__, self).__setattr__(name, value)



if(__name__=='__main__'):
#    tester = someClass()
#    tester.varOne = "Hello"
#    print("Name of wrapper is: ", tester.__class__.__name__)
#    print("Name of class is: ", tester.__name__)
#    print("tester object, ", tester, " var zero: ", tester.varZero, ", var one: ", tester.varOne)
    localSys = isoSys(name='localSys')
    #print('Made isoSys')
    fakeManager = testObj()
    #print('made test object / manager')
    secondObj = secondTestObj()
    #print('made secondary test object')
    fakeManager.objList.append(secondObj)
    #print('added secondary test object to manager\'s object list.')
    fakeManager.polServer = polariServer(name='testServer', displayName='displayName', hostSystem=localSys, manager=fakeManager)
    #print("OBJECT TREE ON MANAGER AFTER SERVER CREATION: ", fakeManager.objectTree)
    print('Created polariServer with a set manager.')
    fakeManager.polServer.startupPolariServer()
    print('Finished setting up server for manager object.')
    