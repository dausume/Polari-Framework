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
        className = str(type(passedInstance).__name__)
        if className not in self.tables:
            return
        # SQLite-serializable types
        serializableTypes = (str, int, float, bool, bytes, type(None))
        # Get actual table columns from the DB schema
        dbFilePath = os.path.join(self.Path, self.name + '.db') if self.Path else self.name + '.db'
        dbConnection = sqlite3.connect(dbFilePath)
        dbCursor = dbConnection.cursor()
        dbCursor.execute(f"PRAGMA table_info({className})")
        tableColumns = [col[1] for col in dbCursor.fetchall()]
        # Collect only attributes that match table columns and are serializable
        rowList = []
        valueList = []
        classInfoDict = passedInstance.__dict__
        for colName in tableColumns:
            if colName == '_branch_path':
                continue  # Handle separately below
            if colName in classInfoDict:
                value = classInfoDict[colName]
                if value is None or value == []:
                    continue
                # Convert lists/dicts to JSON strings
                if isinstance(value, (list, dict)):
                    import json
                    value = json.dumps(value, default=str)
                elif not isinstance(value, serializableTypes):
                    value = str(value)
                rowList.append(colName)
                valueList.append(value)
        # Add _branch_path if the table supports it
        if '_branch_path' in tableColumns:
            try:
                if className in self.manager.objectTypingDict:
                    polyTypedObj = self.manager.objectTypingDict[className]
                    treePath = polyTypedObj.serializeTreePath(passedInstance)
                    if treePath is not None:
                        rowList.append('_branch_path')
                        valueList.append(treePath)
            except Exception:
                pass
        if len(rowList) == 0:
            return
        # Build INSERT OR REPLACE to handle re-persisting on restart
        placeholders = ', '.join(['?'] * len(rowList))
        columns = ', '.join(rowList)
        commandString = f'INSERT OR REPLACE INTO {className} ({columns}) VALUES({placeholders});'
        valueTuple = tuple(valueList)
        try:
            dbCursor.execute(commandString, valueTuple)
            dbConnection.commit()
        except Exception as e:
            print(f'[DB] INSERT failed for {className}: {e}', flush=True)
        dbConnection.close()

    #Returns a List of Two Lists, the first of which contains the class variables, and the
    #second of which is the list of all instances as tuples of the requested class, which have
    #the same order as and are the corresponding values of the first list.
    def getAllInTable(self, tableName):
        commandString = 'SELECT * FROM ' + tableName + ';'
        dbFilePath = os.path.join(self.Path, self.name + '.db') if self.Path else self.name + '.db'
        dbConnection = sqlite3.connect(dbFilePath)
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
            # If polyTypedVars analysis has been populated, use smart schema generation
            if classTypingObj is not None and classTypingObj.polyTypedVarsDict:
                classTypingObj.makeTypedTableFromAnalysis()
                return
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
        dbFilePath = os.path.join(self.Path, self.name + '.db') if self.Path else self.name + '.db'
        if not self.isRemote and os.path.exists(dbFilePath):
            commandString = 'CREATE TABLE IF NOT EXISTS ' + tableName + ' ('
            i = 0
            rowCount = len(rowList)
            while(i < rowCount - 1):
                commandString = commandString + rowList[i] + ', '
                i = i + 1
            commandString = commandString + rowList[rowCount - 1] + ');'
            dbConnection = sqlite3.connect(dbFilePath)
            dbCursor = dbConnection.cursor()
            try:
                dbCursor.execute(commandString)
                dbConnection.commit()
                self.tables.append(tableName)
            except Exception as e:
                print(f'[DB] CREATE TABLE failed for {tableName}: {e}', flush=True)
                print(f'[DB] SQL: {commandString}', flush=True)
            dbConnection.close()

    #Loads the metadata about the database into python by connecting to the already existing database's file
    def loadDB_byFile(self, filePath):
        dbFilePath = os.path.join(filePath, self.name + '.db')
        if(os.path.exists(dbFilePath)):
            dbConnection = sqlite3.connect(dbFilePath)
            dbCursor = dbConnection.cursor()
            dbCursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            # fetchall returns tuples like ('tableName',) — extract plain strings
            rawTables = dbCursor.fetchall()
            self.tables = [row[0] if isinstance(row, tuple) else row for row in rawTables]
            dbConnection.commit()
            dbConnection.close()
        else:
            print(f"Error: Database file not found at {dbFilePath}")

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