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
#from defineIdentities import Identity
#from polariAI.defineConcepts import Concept
#from polariAI.defineMemories import Mem
#from defineExecutables import Executable
#from polariFiles.managedFolders import managedFolder
#from polariFrontendManagement.managedApp import managedApp

from polariFiles.managedFiles import managedFile
from polariFiles.dataChannels import *
from sqlite3 import Error
import os, json, sqlite3, sys

DBtypesList = ['Polari', 'App', 'Test']
DBstatuses = ['UnInitialized Tables', 'Finalized DB']

class managedDatabase(managedFile):
    #Creates an anonymous Database, used only when looking to load a pre-existing Database
    @treeObjectInit
    def __init__(self, name=None, manager=None, DBurl=None, DBtype=None, tables=[], inRAM=False):
            managedFile.__init__(self, name=name, extension='db')
            if(DBtype in DBtypesList or DBtype == None):
                self.DBtype = DBtype
            else:
                logging.warning('Entered an invalid Database Type')
            self.tables = tables
            self.DBstatus = ['UnInitialized DB']
            self.isRemote = None

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

    def validateInitParameters(self, name, isRemote, DBurl, DBfile, DBtype, tables):
        #This is the case where a new Database of a particular type is being defined.
        if(isinstance(name, str) and isinstance(DBtype, str) and isinstance(tables, list)):
            if(DBtypesList.__contains__(DBtype)):
                if(DBtype == 'Polari'):
                    return (True, 'Polari')
                elif(DBtype == 'LocalApp'):
                    return (True, 'LocalApp')
                elif(DBtype == 'Test'):
                    return (True, 'Test')
                return (False, 'Invalid Entries for name, Database Type, or Table Rows.')
        elif(name==None and isRemote==False and DBurl==None and DBtype==None and tables==[]):
            #This is the case where a blank DB instance is defined so that data can be loaded to it later.
            if(DBfile==None):
                print('Generated a Placeholder Database Instance.')
                return (True, 'Placeholder')
            elif(isinstance(DBfile, str)):
                print('Load the DB from a DB file.')
                return (True, 'Awaiting Load From File Command.')
        else:
            return (False, 'Invalid Entry Format.  Either use Default (No Parameter) and then load the DB, '
            +'or enter only the DB file name to load it, or enter the DB name and a valid type as strings.')

    def createDatabase(self):
        self.createFile()

    def saveInstanceInDB(self, passedInstance):
        print('saving instance in DB table.. ' + str(type(passedInstance).__name__))
        if(str(type(passedInstance).__name__) in self.tables):
            classInfoDict = passedInstance.__dict__
            commandString = 'INSERT INTO ' + str(type(passedInstance).__name__) + ' ('
            rowList = []
            valueList = []
            #print('Before the loop..')
            for someVariableKey in classInfoDict.keys():
                if(not callable(someVariableKey)):
                    value = getattr(passedInstance, someVariableKey)
                    #print('Value: ' + str(value))
                    if(someVariableKey == 'name'):
                        if(value == None):
                            logging.warn('Trying to save an un-named class instance.')
                            return None
                    if(value != None and value != []):
                        #print('Recorded Key-Value: ' + str(someVariableKey) + ' - ' + str(value))
                        rowList.append(someVariableKey)
                        valueList.append(value)
            #print('After the loop..')
            if( len(rowList) > 0 ):
                #print('Length of rowList greater than one..')
                i = 0
                while i < len(rowList) - 1:
                    commandString += str(rowList[i]) + ', '
                    i += 1
                commandString += str(rowList[len(rowList) - 1]) + ') VALUES('
                i = 0
                valueTuple = None
                while i < len(valueList) - 1:
                    #valueList.append(str(valueList[i]))
                    commandString += '?, '
                    i += 1
                #valueList.append(str(valueList[len(valueList) - 1]))
                #commandString += str(valueList[len(valueList) - 1])
                commandString +=  '?);'
                valueTuple = tuple(valueList)
                print(valueTuple)
            else:
                logging.warn(msg='Instance without values passed!')
            if(self.Path != None):
                dbConnection = sqlite3.connect(self.Path + self.name + '.db')
            else:
                dbConnection = sqlite3.connect(self.name + '.db')
            dbCursor = dbConnection.cursor()
            try:
                dbCursor.execute(commandString,valueTuple)
                dbConnection.commit()
            except:
                logging.warning(msg='An instance with this name already exists in the DB.')
            dbConnection.close()

    #Returns a List of Two Lists, the first of which contains the class variables, and the
    #second of which is the list of all instances as tuples of the requested class, which have
    #the same order as and are the corresponding values of the first list.
    def getAllInTable(self, tableName):
        commandString = 'SELECT * FROM ' + tableName + ';'
        if(self.Path != None):
            dbConnection = sqlite3.connect(self.Path + self.name + '.db')
        else:
            dbConnection = sqlite3.connect(self.name + '.db')
        dbCursor = dbConnection.cursor()
        print(commandString)
        dbCursor.execute(commandString)
        dataSets = dbCursor.fetchall()
        columns = dbCursor.description
        columnNames = []
        for column in columns:
            columnNames.append(column[0])
        tempList = [columnNames, dataSets]
        dataSets = tuple(tempList)
        dbConnection.close()
        return dataSets

    #Uses a Directory Path and file name together with a class name to import a specific class
    #The Directory Path must exist either at the same location the class is defined or at 
    #Then creates a table by grabbing data from that Class, with all data types set to Text.
    def makeTableByClass(self, absDirPath, definingFile, className):
        #compares the absolute paths of this file and the directory where the class is defined
        #the first character at which the two paths diverge is stored into divIndex
        if(absDirPath != None and definingFile != None and className != None):
            classInstantiationMethod = getAccessToClass(absDirPath, definingFile, className, returnMethod=True)
            defaultClassInstance = classInstantiationMethod()
            classInfoDict = defaultClassInstance.__dict__
            classElementRows = []
            classTypingObj = None
            for objTyping in (self.manager).objectTyping:
                if(objTyping.className == className):
                    classTypingObj = objTyping
                    break
            #The case where no typing information has been entered for the object related to tables
            if(classTypingObj.identifiers == [] and classTypingObj.polyTypedVars == []):
                for classElement in classInfoDict:
                    if(not callable(classElement)):
                        #Allocates all variables to a generalized text type if they are not defined
                        if(classElement == 'name' or classElement == 'identifier'):
                            classElementRows.append((classElement + ' text' + ' PRIMARY KEY'))
                        elif((self.tables).__contains__(classElement)):
                            classElementRows.append((classElement + ' text' + ' FOREIGN KEY'))
                        else:
                            classElementRows.append((classElement + ' text'))
            elif(classTypingObj.identifiers != []):
                for classElement in classInfoDict:
                    if(not callable(classElement)):
                        #Allocates all variables to a generalized text type if they are not defined
                        if((self.tables).__contains__(classElement)):
                            classElementRows.append((classElement + ' text' + ' FOREIGN KEY'))
                        else:
                            classElementRows.append((classElement + ' text'))
            self.makeSQLiteTable(tableName=className, rowList=classElementRows)
        else:
            print("Make sure to enter all three parameters into the makeTableByClass function!  Enter the"
            +"absolute directory path to the folder of the class to be made into a Database table first, then"
            + "enter the name of the file (without extension) where the class is defined second, then enter"
            +"the class name third.")

    #Takes in a table name and a list of strings, with each string having (Keyword, data type,
    #special conditions)
    def makeSQLiteTable(self, tableName, rowList):
        if not self.isRemote and os.path.exists(self.Path + self.name + '.db'):
            commandString = 'CREATE TABLE IF NOT EXISTS ' + tableName + ' ('
            i = 0
            rowCount = len(rowList)
            while(i < rowCount - 1):
                commandString = commandString + rowList[i] + ', '
                i = i + 1
            commandString = commandString + rowList[rowCount - 1] + ');'
            print(commandString)
            dbConnection = sqlite3.connect(self.Path + self.name + '.db')
            dbCursor = dbConnection.cursor()
            try:
                dbCursor.execute(commandString)
                dbConnection.commit()
            except:
                logging.warn(msg='A table with this name alreaady exists in the Database!')
            dbConnection.close()
            self.tables.append(tableName)

    #Loads the metadata about the database into python by connecting to the already existing database's file
    def loadDB_byFile(self, filePath):
        if(os.path.exists(filePath + self.name + '.db')):
            dbConnection = sqlite3.connect(filePath + self.name + '.db')
            dbCursor = dbConnection.cursor()
            dbCursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            self.tables = dbCursor.fetchall()
            dbConnection.commit()
            dbConnection.close()
        else:
            print("Error: Database file not found at location " + filePath + " cannot load database, dumbass.")

    #Recieves metadata about the database 
    def loadDB_byJSON(self, jsonString):
        if(jsonString[0]['class'] == 'managedDataBase'):
            self.name = jsonString[0]['data']['name']
            self.DBfile = jsonString[0]['data']['DBfile']
            self.DBtype = jsonString[0]['data']['DBtype']
            self.tables = jsonString[0]['data']['tables']
        else:
            print("Error: Passed string was not a valid database defining json string, stop fucking up json.")

    def loadDB_byDB(self, dbPath):
        if(os.path.exists(dbPath)):
            dbConnection = sqlite3.connect(dbPath)
            dbCursor = dbConnection.cursor()
            dbCursor.execute("SELECT name, DBfile, DBtype, tables"
            + "FROM managedDataBase WHERE name=" + self.name)
            self.tables = dbCursor.fetchall()
            dbConnection.commit()
            dbConnection.close()
        else:
            print("Error: Database file not found at location " + dbPath + " cannot load database, dumbass.")