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
import os, psutil, json, sqlite3, sys, time, datetime, importlib
#Returns the initialization function for a class -> used so that the Polarity can instantiate any Python Classes
def getAccessToClass(absDirPath, definingFile, className, returnMethod=False):
    #compares the absolute paths of this file and the directory where the class is defined
        #the first character at which the two paths diverge is stored into divIndex
        if(absDirPath != None and definingFile != None and className != None):
            curPath =  (os.path.realpath(__file__))[:os.path.realpath(__file__).rfind('\\')]
            divIndex = 0
            for charIndex in range( len(absDirPath) ):
                if(absDirPath[charIndex] != curPath[charIndex]):
                    divIndex = charIndex
                elif(charIndex == len(absDirPath)):
                    divIndex = None
                divIndex += 1
            if(divIndex == 0 or divIndex == None):
                print("Warning: Make sure you enter an Absolute Path to your class's directory and that it lies"
                + "in the same File System where your Polari is Defined. /n" + " The path entered was: "
                + absDirPath + "/n Error: Either no Directory Path was given or it was invalid.")
            elif(divIndex != len(curPath)):
                print("The path to the file defining the class is not within a subdirectory managable by the Polari./n"
                + "The Path to the class must begin with: " + curPath + "/nThe Path entered was: " + absDirPath)
            else: #Eliminating the previous two possibilites means the absDirPath is in the same Dir or a subDir of curDir
                if(len(absDirPath) > len(curPath)):
                    sys.path.append(absDirPath[divIndex:]) #Gets the subpath relative to the managedDatabase File
                moduleImported = __import__(name=definingFile, fromlist=className)
                ClassInstantiationMethod = getattr(moduleImported, className)
                if(returnMethod):
                    return ClassInstantiationMethod
        else:
            print("Make sure to enter all three parameters into the makeTableByClass function!  Enter the"
            +"absolute directory path to the folder of the class to be made into a Database table first, then"
            + "enter the name of the file (without extension) where the class is defined second, then enter"
            +"the class name third.")

def getAccessToFunctionDefault(absDirPath, definingFile, varFunction):
    #compares the absolute paths of this file and the directory where the class is defined
    #the first character at which the two paths diverge is stored into divIndex
    timeStamp = datetime.now() #Date-Time Stamp of when this initial measure was taken
    if(absDirPath != None and definingFile != None and varFunction != None):
        curPath = os.path.realpath(__file__)
        divIndex = 0
        for charIndex in range( len(absDirPath) ):
            if(absDirPath[charIndex] != curPath[charIndex]):
                divIndex = charIndex
            elif(charIndex == len(absDirPath)):
                divIndex = None
        if(divIndex == 0 or divIndex == None):
            print("Warning: Make sure you enter an Absolute Path to your class's directory and that it lies"
            + "in the same File System where your Polari is Defined. /n" + "The path entered was: "
            + absDirPath + "/nError: Either no Directory Path was given or it was invalid.")
        elif(divIndex != len(curPath)):
            print("The path to the file defining the class is not within a subdirectory managable by the Polari./n"
            + "The Path to the class must begin with: " + curPath + "/nThe Path entered was: " + absDirPath)
        else: #Eliminating the previous two possibilites means the absDirPath is in the same Dir or a subDir of curDir
            if(len(absDirPath) > len(curPath)):
                sys.path.append(absDirPath[divIndex:]) #Gets the subpath relative to the managedDatabase File
            importlib.import_module()

#Allows you to pass a path, file, and function name in order to locate an independent function and call
#it as a default function with no parameters.  Assumes / requires that the function has a Return Value.
def getVarFunctionVelocityMeasurePerSecond(self, absDirPath, definingFile, varFunction, baseFunctionalTimeInterval, timeDeviance):
    getAccessToFunctionDefault(absDirPath, definingFile, varFunction)
    timeVector = []
    timeVector[0] = time.clock() #Start Timer
    timeVector[1] = time.clock() #A second Time Measure Without Interval, to measure base clock function time.
    returnedVal_1 = varFunction()
    timeVector[2] = time.clock() #A third measure how long it takes to grab memory Info using virtual_memory.
    time.sleep(1) #Makes the thread sleep for 1 second or 1000 milliSeconds
    timeVector[3] = time.clock()
    returnedVal_2 = varFunction()
    timeVector[4] = time.clock() #End Time
    t_time = timeVector[1] #Time for the time.clock() function to execute once under the given conditions.
    t_sleep = 1000 #The defined sleep time in milliseconds
    t_intersitial = 0 #Averaged time to transition between two functions during runtime under current conditions.
    t_sleepIO = 0 #The time to enter the constant into the sleep function.
    t_variableFunction = (timeVector[2] - 2*timeVector[1]) #The time for the variable function to execute and return
    t_outerTime = 0 #The time that passes outside of this function in between each recurrence of the function
    t_innerTime = 0 #The time taken for this function to execute overall.
    #First term: To find the apprx time for time.clock() to execute and be assigned, we assume no time exists
    #in between two time.clock() statements and timeVector[n] will be assigned half-way through execution.
    #If this assumption holds true, time.clock() execution time = timeVector[1] - timeVector[0].
    #To account for all time.clock() assignments throughout the function, multiply by 5.
    #
    #Second Term: From timeVector[2], subtract out timeVector[1] such that the consideration of time is
    #between the middle of timeVector[1]'s assignment and timeVector[2]'s assignment. If the previous term
    #is consistently valid, and we consider time between all executions to be 0ms, then the execution time
    #of retrieving and assigning psutil.virtual_memory() is the total time considered less half the execution
    #time of both of the clock() assignments on each side of it. To account for all VM(), multiply by 2.
    #
    #Third Term: Track the interstitial time it takes to initiate and exit the sleep function, take out the
    #expected sleep time
    t_functionOccupiedTime = (4*t_time) + (8*t_intersitial) + (2*t_variableFunction) + (t_sleepIO)
    #The corrected sleep time by negating function time so that readings actually happen every 1000ms
    correctedSleepTimeIntervalConstant = 1000 - baseFunctionalTimeInterval
    actualTimeInterval = timeVector[4]
    theoreticalTimeInterval = baseFunctionalTimeInterval + 1000
    #How much the accountability method of the functions deviates from the actual time produced by them.
    theoryDeviance = actualTimeInterval - theoreticalTimeInterval
    #How much the time of the measuring function deviates from desired Interval per repetition
    expectationDeviance = actualTimeInterval - 1000
    #
    constAndDevianceTupleList = WrapRecursiveVarFunctionVelocityMeasuring(devianceList=[timeDeviance], maxiter=(timeDeviance*2 + 10), iter=0, goalTimeInterval_ms=1000, actualTimeInterval_ms=correctedSleepTimeIntervalConstant)

#Wraps the recursive process for analyzing the time interval between measures of memory.
def WrapRecursiveVarFunctionVelocityMeasuring(self, constAndDevianceHistory, maxiter, iter, goalTimeInterval_ms, actualTimeInterval_ms):
    startRecursionTime = time.clock()
    constAndDevianceHistory = RecursiveVarFunctionVelocityMeasuring(constAndDevianceHistory, maxiter, iter, goalTimeInterval_ms, actualTimeInterval_ms)
    endRecursionTime = time.clock()

def RecursiveVarFunctionVelocityMeasuring(self, devianceTupleList, const, maxiter, iter, goalTimeInterval_ms, actualTimeInterval_ms):
    timeVector = []
    timeVector[0] = time.clock() #If this does not work, use time.time()
    timeVector[1] = time.clock()
    mainMemoryInfo = psutil.virtual_memory()
    timeVector[2] = time.clock()
    time.sleep(const)
    timeVector[3] = time.clock()
    mainMemoryInfo = psutil.virtual_memory()
    timeVector[4] = time.clock() #Should be pretty close to the goal time.
    baseFunctionalTimeInterval = (timeVector[1]*5) + (timeVector[2] - 2*timeVector[1]) + (timeVector[3] - (timeVector[2] + timeVector[1] + 1000))
    newSleepTimeIntervalConstant = 1000 - baseFunctionalTimeInterval
    functionalTimeDeviance = const - newSleepTimeIntervalConstant
    actualTimeInterval = timeVector[4]
    theoreticalTimeInterval = baseFunctionalTimeInterval + 1000
    timeDeviance = actualTimeInterval - theoreticalTimeInterval
    if(goalTimeInterval_ms == actualTimeInterval_ms):
        devianceTupleList.add(goalTimeInterval_ms - actualTimeInterval_ms, datetime.now())
        timesMatched = 0
        for i in devianceTupleList:
            if(devianceTupleList[0] == 0):
                timesMatched += 1
        print('Perfectly Calibrated ' + timesMatched + 'times!')
    elif(iter < maxiter):
        print('Keep trying to Calibrate!!  Current time deviance is: ' + (goalTimeInterval_ms - actualTimeInterval_ms) + 'ms.')
        #if()
    else:
        print('Calibrated for ' + iter + ' iterations, deviance is')