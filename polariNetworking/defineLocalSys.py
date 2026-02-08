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
import os
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
        self.systemType = platform.system()
        self.networkName = os.environ.get('HOSTNAME', platform.node())
        self.domainName = os.environ.get('DOMAINNAME', socket.getfqdn())
        # Resolve actual IP address from hostname
        try:
            self.IPaddress = socket.gethostbyname(socket.gethostname())
        except socket.gaierror:
            self.IPaddress = '127.0.0.1'
        # Detect if networkName looks like a Docker container ID (12-char hex)
        self.isContainerized = bool(re.fullmatch(r'[0-9a-f]{12,64}', self.networkName))
        #self.internetServiceProvider
        sysMetrics = None
        #Graphics, Screen, and Monitor information for the system
        if(self.systemType == 'Windows'):
            if(ctypes.sizeof(ctypes.c_void_p) == 4):
                sysMetrics = ctypes.windll.user32
                #Height and width of the main monitor used for the system by default
                self.mainMonitorPixelWidth = sysMetrics.GetSystemMetrics(0)
                self.mainMonitorPixelHeight = sysMetrics.GetSystemMetrics(1)
                #Height and width of a Virtual Monitor which may be composed of multiple Monitors
                self.virtualMonitorPixelWidth = sysMetrics.GetSystemMetrics(78)
                self.virtualMonitorPixelHeight = sysMetrics.GetSystemMetrics(79)
                sysMetrics.SetProcessDPIAware()
                #Gets the number of monitors connected to the system
                self.NumMonitors = sysMetrics.GetSystemMetrics(80)
        #app = QApplication(sys.argv)
        #screen = app.screens()[0]
        #dpi = screen.physicalDotsPerInch()
        #app.quit()
        #self.PixelsPerInch = dpi
        #Memory Information about the main system
        self.numPhysicalCPUs = psutil.cpu_count(False)
        self.numLogicalCPUs = psutil.cpu_count(True)
        #THE FOLLOWING LINE CAUSED AN ERROR OF INVALID TYPE - WAS DEPRICATED?
        #self.perCPUfreqInMegaHertz = psutil.cpu_freq(percpu=True)
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

    def refreshMetrics(self):
        """Re-read current memory, swap, and CPU usage from the host system."""
        timeStamp = str(datetime.now())
        mainMemoryInfo = psutil.virtual_memory()
        self.availableMainMemoryInBytes = (mainMemoryInfo[1], timeStamp)
        self.percentMainMemoryUsed = (mainMemoryInfo[2], timeStamp)
        self.usedMainMemoryInBytes = (mainMemoryInfo[3], timeStamp)
        self.freeMainMemoryInBytes = (mainMemoryInfo[4], timeStamp)
        swapMemoryInfo = psutil.swap_memory()
        self.swappedOutMemory = (swapMemoryInfo[4], timeStamp)
        self.swappedInMemory = (swapMemoryInfo[3], timeStamp)
        self.freeSwapMemoryInBytes = (swapMemoryInfo[2], timeStamp)
        self.usedSwapMemoryInBytes = (swapMemoryInfo[1], timeStamp)
        self.currentCpuPercent = psutil.cpu_percent(interval=0.1)

    # --- Bootstrapping path utilities ---
    # These static methods exist for the bootup/bootstrapping phase where modules
    # are being loaded and source files located before any isoSys instance is available.
    # They use platform.system() to detect the host OS and delegate to os.path so paths
    # resolve correctly on Windows, Linux, and macOS.

    @staticmethod
    def bootupPathSep():
        """Returns the OS-appropriate path separator for use during bootstrapping."""
        if platform.system() == 'Windows':
            return '\\'
        return '/'

    @staticmethod
    def bootupPathJoin(*args):
        """Joins path components using the OS-appropriate separator during bootstrapping."""
        return os.path.join(*args)

    @staticmethod
    def bootupPathDir(filepath):
        """Returns the directory portion of a file path during bootstrapping."""
        return os.path.dirname(filepath)

    @staticmethod
    def bootupPathFile(filepath):
        """Returns the filename (with extension, without directory) from a file path during bootstrapping."""
        return os.path.basename(filepath)

    @staticmethod
    def bootupPathSplit(filepath):
        """Splits a path into (directory, filename) tuple during bootstrapping."""
        return os.path.split(filepath)

    @staticmethod
    def bootupPathStem(filepath):
        """Returns filename without extension from a full path during bootstrapping."""
        return os.path.splitext(os.path.basename(filepath))[0]

    def powerShellCommand(self, commandString, decodeMethod):
        process = subprocess.Popen(['powershell', commandString], stdout=subprocess.PIPE)
        resolve = process.communicate()
        #Checks that no errors occurred when attempting the process
        if(resolve[1] == None and decodeMethod == None):
            result = resolve[0]
            if(validDecodeMethods.__contains__(decodeMethod)):
                result = resolve.decode(decodeMethod)