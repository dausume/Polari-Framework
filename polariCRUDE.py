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


from objectTreeDecorators import *
from polariPermissionSet import polariPermissionSet
from functionalityAnalysis import getAccessToClass
import json
import setOperators
import falcon

#Defines the Create, Read, Update, and Delete Operations for a particular api endpoint designated for a particular dataChannel or polyTypedObject Instance.
class polariCRUDE(treeObject):
    @treeObjectInit
    def __init__(self, apiObject, polServer):
        self.polServer = polServer
        endpointList = self.polServer.uriList
        if('/' + apiObject in endpointList or '\\' + apiObject in endpointList):
            raise ValueError("Trying to define an api for uri that already exists on this server.")
        #The polyTypedObject or dataChannel Instance
        self.apiObject = apiObject
        self.apiName = '/' + apiObject
        self.objTyping = self.manager.objectTypingDict[self.apiObject]
        #Basis Access Dictionaries granted to anyone accessing the API.
        self.baseAccessDictionaries = []
        self.basePermissionDictionaries = []
        #Get the instantiation method for the class, for use in the CREATE method.
        self.CreateMethod = self.objTyping.getCreateMethod()
        self.CreateParameters = list(inspect.signature(self.CreateMethod).parameters)
        #Go through each polyTyped variable and get all variables on it.
        for someVarTyping in self.objTyping.polyTypedVars:
            pass
        if(polServer != None):
            polServer.falconServer.add_route(self.apiName, self)

    #1. Returns an Access Permissions for the given object for the given operation
    #being performed, in the format of a set of different object queries and the
    #variables they are allowed access to with the given dataSets.
    #2. For instances existing in multiple dataSets (found through an Intersection
    #operation between the different dataSets), there is a union of all
    #variables from the dataSets it is found to exist in.  For that set of variables
    #created by that union, we see if a dataSet with those variables exists.  If it
    #does exist, we add it.  Else, we create a new dataSet with those variables.
    def getUsersObjectAccessPermissions(self, userInfo):
        #Pass back the minimal permissions to the object allowed for people who
        #have yet to be able to login.
        if(userInfo == None):
            #(self.objTyping.basePermissionsDict, self.objTyping.baseAccessDict)
            return {'R':{self.apiObject:"*"}, 'E':{self.apiObject:"*"}}, {'R':([],{self.apiObject:"*"}), 'E':([],{self.apiObject:"*"})}
        #Get the user and compile a permissions dictionary for the object based on
        #the permissions tied to the user.
        else:
            return {'R':{self.apiObject:"*"}, 'E':{self.apiObject:"*"}}, {'R':([],{self.apiObject:"*"}), 'E':([],{self.apiObject:"*"})}

    #Read in CRUD
    def on_get(self, request, response):
        #Get the authorization data, user data, and potential url parameters, which are both commonly relevant to both cases.
        print("Starting GET method.")
        userAuthInfo = request.auth
        print("request.auth : ", request.auth)
        #Create a list of all 
        (accessQueryDict, permissionQueryDict) = self.getUsersObjectAccessPermissions(userAuthInfo)
        #Check to ensure user has at least some access.
        if(not "R" in accessQueryDict):
            response.status = falcon.HTTP_405
            raise PermissionError("Read or Get requests not allowed at all for this user on this object type.")
        if(not "R" in permissionQueryDict):
            response.status = falcon.HTTP_405
            raise PermissionError("Read or Get requests do not have access to any variables on this object type.")
        #authUser = request.context.user
        print("request.context : ", request.context)
        print("request.query_string : ", request.query_string)
        #TODO Instead of comparing the sets, make functionality to instead create
        #operators to compare the queries and generate a new query based on their
        #differences.  Then just directly get the instances using the retrievable
        #instances query.
        #
        #Get which instances fall under what is being requested.
        requestedQuery = request.query_string
        #Get which instances 
        allowedQuery = accessQueryDict["R"][self.apiObject]
        #Cross analyze requested Instances and allowed instances (according to Access
        #Dictionaries on user) in order to analyze which instances requested are able
        #to be returned, in other words it performs 'viewing access'. 
        requestedInstances = self.manager.getListOfInstancesByAttributes(className=self.apiObject, attributeQueryDict=accessQueryDict )
        #allowedInstances = self.manager.getListOfInstancesByAttributes(className=self.apiObject, attributeQueryDict=allowedQuery )
        #retrievableInstances = self.instanceSetIntersection(requestedInstances, retrievableInstances)
        #TODO Add functionality to sort retrievableInstances into different sets
        #of variables with allowed read access.
        #
        #Returns a list of tuples [([restricted Vars List],[List Of Instances]), dataSetTuple2, ...]
        #dataSetQueriesList = setOperators.segmentDataSetsByPermissions(retrievableInstances, permissionQueryDict)
        #urlParameters = request.query_string
        print("Got auth, context.user, and queryString data.")
        jsonObj = {}
        try:
            if(requestedInstances != {}):
                #jsonObj[self.apiObject] = self.manager.getJSONdictForClass(passedInstances=retrievableInstances)
                #For now we just give everything being requested and don't bother with permissions
                jsonObj[self.apiObject] = self.manager.getJSONdictForClass(passedInstances=requestedInstances)
            else:
                jsonObj[self.apiObject] = {}
            response.media = [jsonObj]
            response.status = falcon.HTTP_200
        except Exception as err:
            response.status = falcon.HTTP_500
            print(err)
            #raise falcon.HTTPServiceUnavailable(
            #    title = 'Service Failure on Manager',
            #    description = ('Encountered error while trying to get objects on given manager.'),
            #    retry_after=60
            #)
        response.set_header('Powered-By', 'Polari')

    def on_get_collection(self, request, response):
        pass

    #Update in CRUD
    def on_put(self, request, response):
        print("In Update API execution segment.")
        print("Request: ", request)
        userAuthInfo = request.auth
        print("request.auth : ", request.auth)
        (accessQueryDict, permissionQueryDict) = self.getUsersObjectAccessPermissions(userAuthInfo)
        #Check to ensure user has at least some access to events.
        if(not "U" in accessQueryDict):
            response.status = falcon.HTTP_405
            raise PermissionError("Event requests not allowed at all for this user on this object type.")
        #Determines which events can be accessed.
        if(not "U" in permissionQueryDict):
            response.status = falcon.HTTP_405
            raise PermissionError("Event requests do not have access to any variables on this object type.")
        data = request.get_media()
        for someData in data:
            print("data segment name: ",someData.name)
            print("data segment content type: ",someData.content_type)
            print("data segment: ", someData.data)
            dataSegment = (someData.data).decode("utf-8")

    def on_put_collection(self, request, response):
        pass

    #Create object instances in CRUDE
    def on_post(self, request, response):
        userAuthInfo = request.auth
        authUser = request.context.user
        urlParameters = request.query_string
        (accessQueryDict, permissionQueryDict) = self.getUsersObjectAccessPermissions(userAuthInfo)
        data = request.get_media()
        dataSets = []
        dataSet = {}
        for someData in data:
            print("content type: ",someData.content_type)
            dataSegment = (someData.data).decode("utf-8")
            #THE FOLLOWING TWO ARE USED IF THE POST CONSISTS OF A SINGULAR DATASET
            #A dictionary of objects to a list of dictionaries {"obj0":[{"var":"", "instanceQuery":query}]}
            if(someData.name == "attachmentPoints"):
                dataSet["attachmentPoints"] = json.loads(dataSegment)
            if(someData.name == "newInstances"):
                dataSet["newInstances"] = json.loads(dataSegment)
            #THIS IS USED IF MULTIPLE DATASETS ARE BEING SENT AT ONCE
            #A list of dataSets where [{"obj0":[{"var":"varName", "instanceQuery":query}]}],"initParams":[{"param0":val0, "param1":val1}]}]
            if(someData.name == "dataSets"):
                dataSets = json.loads(dataSegment)
        if(dataSet != {}):
            dataSets.append(dataSet)
        allowedUpdatesAccessDict = {}
        allowedUpdatesPermissionsDict = {}
        tempInstancesList = []
        for someDataSet in dataSets:
            #Take given json entries and create a list of temporary instances from it.
            for newInst in someDataSet["newInstances"]:
                #Use the __init__ funtion for this api's object to create new instances using variables passed.
                #Add the new instances to the list of temporary instances.
                #After all instances are created we will run a query operation on them to ensure the user
                #should be allowed to create them in the given criteria.
                pass
            #Resolve queries for attachmentPoints and run user access validation.
            for someObj in someDataSet["attachmentPoints"].keys():
                #Get which instances we are allowed to allocate these new instances onto.
                if(not someObj in allowedUpdatesAccessDict.keys()):
                    allowedQuery = accessQueryDict["U"][self.apiObject]
                    allowedUpdatesAccessDict[someObj] = self.manager.getListOfInstancesByAttributes(className=someObj, attributeQueryDict=accessQueryDict )
                    permissionQuery = permissionQueryDict["U"][self.apiObject]
                    allowedUpdatesPermissionsDict[someObj] = self.manager.getListOfInstancesByAttributes(className=someObj, attributeQueryDict=permissionQuery )
                #Resolve the attachment point queries.  Check their resolved instance lists
                #against the allowedAccess and allowedPermissions query resolutions.
                #If there are any mismatches, throw an error.
                for somePointSet in someDataSet["attachmentPoints"][someObj]:
                    attachmentInstances = self.manager.getListOfInstancesByAttributes(className=someObj, attributeQueryDict=somePointSet["instanceQuery"] )
                    for id in attachmentInstances.keys():
                        for newInst in tempInstancesList:
                            attrRef = getattr(attachmentInstances[id], somePointSet["var"])
                            attrType = attrRef.__class__.__name__
                            if(attrType == "polariList" or attrType == "list"):
                                attrRef.append(newInst)
                            elif(attrRef == None):
                                attrRef = newInst
                            elif(attrType in self.manager.objectTypingDict.keys()):
                                #TODO Delete the reference if it is a duplicate, migrate main ref if another 
                                #reference exists for the instance being replaced, or delete the reference and
                                #perform a similar action to all referenced nodes dependent on it...
                                #TEMPORARILY we will just replace it and ignore all that though.
                                attrRef = newInst
                            #allocate the reference onto the manager tree.
                            attrRef.manager = self.manager
        #With all validation of permissions complete and queries resolved, we go through
        #the attachment points and place each instance followed by setting it's manager.


    def on_post_collection(self, request, response):
        pass

    #Delete in CRUD
    def on_delete(self, request, response):
        authSession = request.auth
        authUser = request.context.user
        urlParameters = request.query_string
        #if(self.objType == 'polyTypedObject'):
            #
        #elif(self.objType == 'dataChannel'):
            #

    def on_delete_collection(self, request, response):
        pass

    def on_event(self, request, response):
        print("In Event API execution segment.")
        print("Request: ", request)
        userAuthInfo = request.auth
        print("request.auth : ", request.auth)
        (accessQueryDict, permissionQueryDict) = self.getUsersObjectAccessPermissions(userAuthInfo)
        #Check to ensure user has at least some access to events.
        if(not "E" in accessQueryDict):
            response.status = falcon.HTTP_405
            raise PermissionError("Event requests not allowed at all for this user on this object type.")
        #Determines which events can be accessed.
        if(not "E" in permissionQueryDict):
            response.status = falcon.HTTP_405
            raise PermissionError("Event requests do not have access to any variables on this object type.")
        data = request.get_media()
        targetInfo = {}
        event = ""
        parametersDict = {}
        for someData in data:
            print("data segment name: ",someData.name)
            print("data segment content type: ",someData.content_type)
            print("data segment: ", someData.data)
            dataSegment = (someData.data).decode("utf-8")
            #Find if target can be found using passed variable info.
            #If the variables passed in do not resolve to exactly one target,
            #then throw an error.
            if(someData.name == "targetInstance"):
                targetInfo = json.loads(dataSegment)
            if(someData.name == "event"):
                #get the function info from the object and confirm it exists.
                event = dataSegment
            #Get event parameters, ensure there are no duplicates being defined.
            #Each of the following are optional methods that can be used to define parameters.
            paramsDictionary = {}
            #literalParams: Literal values passed as parameters from this request into the event.
            #instanceListQueryParams: A query that gets a list of instances to be passed into a set of parameters for the event.
            #varListQueryParams: A query that gets a list of values for a single variable from a list of instances and
            #passes them into a set of parameters defined for the event.
            #instanceQueryParams: A query that gets a single specific instance and passes it into into an event parameter.
            #varQueryParams: Gets a specific variable from a certain instance by query and passes it into the parameter.
            validParamOptions = ["varQueryParams", "instanceQueryParams", "literalParams", "instanceListQueryParams", "varListQueryParams"]
            #If one of the options for parameters is passes, add it to the parameters dict.
            if(someData.name in validParamOptions):
                parametersDict[someData.name] = dataSegment
        #Get which instances events are allowed to be run on for this user.
        allowedQuery = accessQueryDict["E"][self.apiObject]
        allowedInstances = self.manager.getListOfInstancesByAttributes(className=self.apiObject, attributeQueryDict=accessQueryDict )
        targetResolution = self.manager.getListOfInstancesByAttributes(className=self.apiObject, attributeQueryDict=targetInfo )
        targetInstance = None
        #First, check if the target info passed can resolve to a single target.
        if(targetInfo == {}):
            raise KeyError("No target Information passed for use in retrieving target.")
        if(len(targetResolution) == 1):
            targetId = list(targetResolution.keys())[0]
            targetInstance = targetResolution[targetId]
            if(targetId not in allowedInstances.keys()):
                raise PermissionError("Permissions do not allow user to perform events on the targeted instance.")
            pass
        else:
            if(len(targetResolution) == 0):
                raise ValueError("Target did not resolve and could not retrieve any instances.")
            else:
                raise ValueError("Target resolved for multiple instances, must resolve to only one.")
        #Second, check that the event exists on the target as a function and get parameters.
        eventRef = None
        allParams = []
        if(hasattr(targetInstance, event)):
            eventRef = getattr(targetInstance, event)
            sig = inspect.signature(eventRef)
            allParams = list(sig.parameters)
            print("Got event ", eventRef, " and parameters list", allParams, " from signature ", sig)
        else:
            raise ValueError("Event could not be found on target.")
        #Third, go through parameter options and attempt to resolve all that are found to exist.
        #
        keywordParams = {}
        #Fourth, call the event's execution using the resolved parameters and get the
        #return value.
        returnVal = eventRef(**keywordParams)
        if(returnVal.__class__.__name__ == "polariUser"):
            returnVal
        setTypes = ["list", "tuple", "polariList"]
        if(returnVal.__class__.__name__ in setTypes):
            response.media = {"return-value":self.manager.convertSetTypeIntoJSONdict(returnVal)}
        elif(returnVal.__class__.__name__ in standardTypesPython):
            response.media = {"return-value":returnVal}
        else:
            response.media = {"return-value":self.manager.getJSONdictForClass(passedInstances=[returnVal])}
        #Take the return value and convert it to a format that can be 
        response.status = falcon.HTTP_200


    #
    def onChannelValidation(self):
        #Does the Channel allow for the particular CRUD action to be performed?
        pass
    #
    def onObjectValidation(self):
        #Does the user have
        pass