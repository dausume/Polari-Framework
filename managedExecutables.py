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
from managedFiles import *

LanguageExtensionsDict = {'py':'python','js':'javascript','html':'hypertextmarkuplanguage','css':'cascadingstylesheets'}

class managedExecutable(managedFile):

    def __init__(self, name=None, extension=None):
        managedFile.__init__(self, name=name, extension=extension)
        #The full name of the software language being used in this file.
        self.language = None
        self.setLanguage()
        #Strings of code within the file that are accounted for using different nodes.
        self.codeStrings = []
        #The corresponding Logic Node Objects to the code strings of the file.
        self.AccountingLogicNodes = []
        #Accounts for which code strings have complete logic within the scope of
        #this one file.
        self.innerContext = []
        #Accounts for which code strings have their logic completed outside the scope
        #of the file, but have those files linked by reference.
        self.outerContext = []

    def setLanguage(self):
        if(self.extension in LanguageExtensionsDict.keys()):
            self.language = LanguageExtensionsDict[self.extension]

    def setExtension(self, fileExtension):
        if(fileExtensions.__contains__(fileExtension)):
            logging.warning('Entered a valid file extension, but instantiated using the wrong object, should be a managedFile.')
        elif(picExtensions.__contains__(fileExtension)):
            logging.warning('Entered a valid image file, but instantiated using the wrong object, should be a managedimage.')
        elif(dataBaseExtensions.__contains__(fileExtension)):
            self.extension = fileExtension
        elif(dataCommsExtensions.__contains__(fileExtension)):
            logging.warning('Entered a valid file extension meant for data transmissions, but instantiated using the wrong object, should be a dataComms object.')
        elif(executableExtensions.__contains__(fileExtension)):
            logging.warning('Entered an invalid or unhandled file Extension.')
        else:
            logging.warning('Entered an invalid or unhandled file Extension.')


    
    