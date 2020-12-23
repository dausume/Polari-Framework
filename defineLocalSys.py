#Defines a single localized system, which is generally a single computer with a single screen.
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
import socket
import subprocess
import re
import platform
import ctypes
import sys
import time
from datetime import datetime
#from win32.win32api import GetSystemMetrics
import psutil
from objectTreeDecorators import *
#from PyQt5 import QApplication

#Defines a class for an isolated system, this case assumes a Windows x32 or x64 system
class isoSys(treeObject):
    #gets information needed for the polari from the local system that this code runs on.
    @treeObjectInit
    def __init__(self, name=None):
        self.name = name
        #Networking Information for the System
        self.networkName = platform.node()
        self.IPaddress = socket.gethostname()
        self.domainName = socket.getfqdn()
        #self.internetServiceProvider
        #Graphics, Screen, and Monitor information for the system
        user32 = ctypes.windll.user32
        user32.SetProcessDPIAware()
        #Height and width of the main monitor used for the system by default
        self.mainMonitorPixelWidth = user32.GetSystemMetrics(0)
        self.mainMonitorPixelHeight = user32.GetSystemMetrics(1)
        #Height and width of a Virtual Monitor which may be composed of multiple Monitors
        self.virtualMonitorPixelWidth = user32.GetSystemMetrics(78)
        self.virtualMonitorPixelHeight = user32.GetSystemMetrics(79)
        #Gets the number of monitors connected to the system
        self.NumMonitors = user32.GetSystemMetrics(80)
        #app = QApplication(sys.argv)
        #screen = app.screens()[0]
        #dpi = screen.physicalDotsPerInch()
        #app.quit()
        #self.PixelsPerInch = dpi
        #Memory Information about the main system
        self.numPhysicalCPUs = psutil.cpu_count(False)
        self.numLogicalCPUs = psutil.cpu_count(True)
        self.perCPUfreqInMegaHertz = psutil.cpu_freq(percpu=True)
        mainMemoryInfo = psutil.virtual_memory() #Fetches Memory Information from the base system functionality
        timeStamp = str(datetime.now())
        self.totalMainMemoryInBytes = mainMemoryInfo[0]
        self.availableMainMemoryInBytes = (mainMemoryInfo[1], timeStamp)
        self.percentMainMemoryUsed = (mainMemoryInfo[2], timeStamp)
        self.usedMainMemoryInBytes = (mainMemoryInfo[3], timeStamp)
        self.freeMainMemoryInBytes = (mainMemoryInfo[4], timeStamp)
        #self.activeMainMemoryInBytes = (mainMemoryInfo[5], timeStamp)
        #self.inactiveMainMemoryInBytes = (mainMemoryInfo[6], timeStamp)
        #self.bufferOccupiedMainMemoryInBytes = (mainMemoryInfo[7], timeStamp)
        #self.cachedMainMemoryInBytes = (mainMemoryInfo[8], timeStamp)
        #self.sharedMainMemoryInBytes = (mainMemoryInfo[9], timeStamp)
        #self.slabMainMemoryInBytes = (mainMemoryInfo[10], timeStamp)
        #self.MainMemoryConsumptionVectorInBytesPerVarMilliSeconds = (None, 1000) #(0 bytes consumed, over 1000 milliseconds OR 1 second)
        swapMemoryInfo = psutil.swap_memory() #Memory Information on extensions for the main system memory
        self.swappedOutMemory = (swapMemoryInfo[4], timeStamp)
        self.swappedInMemory = (swapMemoryInfo[3], timeStamp)
        self.freeSwapMemoryInBytes = (swapMemoryInfo[2], timeStamp)
        self.usedSwapMemoryInBytes = (swapMemoryInfo[1], timeStamp)
        self.totalSwapMemoryInBytes = swapMemoryInfo[0]
        self.SwapMemoryConsumptionVectorInBytesPerVarMilliSeconds = (None, 1000) #(0 bytes consumed, over 1000 milliseconds OR 1 second)

    def powerShellCommand(self, commandString, decodeMethod):
        process = subprocess.Popen(['powershell', commandString], stdout=subprocess.PIPE)
        resolve = process.communicate()
        #Checks that no errors occurred when attempting the process
        if(resolve[1] == None and decodeMethod == None):
            result = resolve[0]
            if(validDecodeMethods.__contains__(decodeMethod)):
                result = resolve.decode(decodeMethod)