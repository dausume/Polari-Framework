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
import inspect

#Events which are triggered (typically) on the client side, which then require some
#functionality to occur on the python side.
#Basically -> allows use of Python functions through an App or Polari object.
#So long as a class or function exists in the scope of the App or Polari manager,
#it will be retrievable from here.
class remoteEvent():
    def __init__(self, eventName=None, source=None, sink=None, channels=[]):
        #The manager of this event, which is either awaiting it's return, preparing to
        #process or propagate it to a higher order object.
        self.manager = None
        #the identifier given to the remoteEvent
        self.identifier = None
        #The event or function that is being triggered remotely
        self.eventName = None
        #Continues to propagate upwards to higher order objects when it arrives at
        #it's designated sink.  This is necessary in order to utilize data analysis with
        #a Polari AI overviewing an application or website server.
        #Ex:sink(app)->appManager(Polari) 
        #OR sink(pageInstance)->Window(User Interface in Python)->User(All UIs & user data)
        self.propagation = False
        #The Response to the event that was or will be sent back to the source of
        #the event.
        self.response = None
        #The time between when the event is sent to the destination
        self.eventTimeout = None
        #The location that is requesting an event to occur and that a resulting
        #response should be returned to.
        self.source = source
        #The location where the desired event or function should occur, and where
        #all of it's parameters should be gaurenteed to arrive at in a paired
        #dataStream instance.
        self.sink = sink
        #A dictionary of key-value pairs where each is a parameter to be passed
        #from the source to the sink for executing the intended event.
        self.parametersDict = {}
        #The dataStream Object which should ensure parameters meant to be passed
        #to the remote operation are sent and exist in their most updated form.
        #(When the event or it's response is sent, the parameter stream should be sent
        #BEFORE the event is sent, to ensure updated values are used for execution)
        self.parameterStream = None

    #Gets all functions on a class, which may be run as events, along with their
    #function comments, parameters, and default values (set as None if not specified).
    #EX:{'functionName':('Comments on Function', [(parameterName0,parameterDefault0),
    # (parameterName1, parameterDefault1),(parameterName2, None)])}
    def getEvents(self):
        eventsDict = {}
        eventsList = inspect.getmembers(self.manager, predicate=inspect.isfunction)

    #Runs the event in the case where it's destination has been reached and should
    #be excuted using python code.
    def runEvent(self):
        #Gets the source file for the class that manages this remoteEvent currently
        managerSourceFile = (self.manager).getsourcefile(object)
        #Gets the string class name of the
        managerClassName = type(self.manager)
        #Gets the actual function/event to be executed on the manager.
        eventToRun = getattr(self.manager, self.eventName)
        #Gets all of the keyword arguments (paramaters) that are able to be passed.
        kwargsTuple = eventToRun.__code__.co_varnames
        #Unpacks the parameters dict that was sent along with the event and calls
        #the function using those parameters on the manager object accordingly.
        try:
            response = (self.manager).eventToRun(**(self.parametersDict))
            if(response == None):
                self.response = {'status':'resolved','response':None}
        except(Exception):
            self.response = {}



    #Makes the event propagate upwards through the manager field
    def propagateEvent(self):
        #Case where the propagation destination has not been reached (the sink).
        #And therefore propagation should continue to execute
        if( (self.manager).name != self.sink):
            if( (self.manager).manager != None ):
                self
            else:
                (self.response)['status'] = ''
        #
        else:
            self.onSink = True


    #
    def sendEvent(self):
        self