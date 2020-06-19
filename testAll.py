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
#Bare minimum tests required to ensure framework segment of the Polari System works.
#Ensures the following Objects work Properly:
#Polari, managedFile, managedDatabase, managedExecutable, isoSys
from managedDB_test import * #managedDatabase
from managedExecutablesTest import * #managedExecutable
from managedFoldersTest import * #managedFolder
from managedImageTest import * #managedImage
from managedFileTest import * #managedFile
from definePolariTest import * #Polari
from defineLocalSysTest import * #isoSys
from managedDataCommsTest import * #dataChannel
if(__name__=='__main__'):
    test0 = managedDB_testClass()
    test1 = managedExecutable_testClass()
    test2 = managedFolder_testClass()
    test3 = managedImage_testClass()
    test4 = managedFile_testClass()
    test5 = Polari_testClass()
    test6 = isoSys_testClass()
    test7 = dataChannel_testClass()
    unittest.main()
