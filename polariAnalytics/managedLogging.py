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
#Makes a logging file which allows you to trace debugging information.
#Where fileName is the name of the file the debug is being run on
#FileLoc is a relative path indicating where debug file should be, if none, it will be in current dir.
from polariFiles.managedFiles import managedFile

class managedLog(managedFile):
    def __init__(self, fileName=None):
        managedFile.__init__(self, fileName=fileName, extension='log')