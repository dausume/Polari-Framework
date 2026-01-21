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
from accessControl.polariPermissionSet import polariPermissionSet
from polariAnalytics.functionalityAnalysis import getAccessToClass
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
        self.CreateMethod  = self.objTyping.getCreateMethod(returnTupWithParams=True)
        self.CreateDefaultParameters = self.objTyping.kwDefaultParams
        self.CreateRequiredParameters = self.objTyping.kwRequiredParams
        #Go through each polyTyped variable and get all variables on it.
        self.validVarsList = []
        for someVarTyping in self.objTyping.polyTypedVars:
            self.validVarsList.append(someVarTyping.name)
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
            #TODO For testing temporarily just give universal access, else give
            #minimal access in this case.
            #(self.objTyping.basePermissionsDict, self.objTyping.baseAccessDict)
            return {'C':{self.apiObject:"*"}, 'R':{self.apiObject:"*"}, 'U':{self.apiObject:"*"}, 'D':{self.apiObject:"*"}, 'E':{self.apiObject:"*"}}, {'C':([],{self.apiObject:"*"}),'R':([],{self.apiObject:"*"}),'U':([],{self.apiObject:"*"}), 'D':([],{self.apiObject:"*"}), 'E':([],{self.apiObject:"*"})}
        #Get the user and compile a permissions dictionary for the object based on
        #the permissions tied to the user.
        else:
            return {'R':{self.apiObject:"*"}, 'E':{self.apiObject:"*"}}, {'R':([],{self.apiObject:"*"}), 'E':([],{self.apiObject:"*"})}

    #Read in CRUD
    def on_get(self, request, response):
        #Get the authorization data, user data, and potential url parameters, which are both commonly relevant to both cases.
        # Verbose request logging - commented out for cleaner output
        # print("Starting GET method.")
        userAuthInfo = request.auth
        # print("request : ", request)
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
        # print("request.context : ", request.context)
        # print("request.query_string : ", request.query_string)
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
        requestedInstances = self.manager.getListOfInstancesByAttributes(className=self.apiObject, attributeQueryDict=accessQueryDict["R"][self.apiObject] )

        #allowedInstances = self.manager.getListOfInstancesByAttributes(className=self.apiObject, attributeQueryDict=allowedQuery )
        #retrievableInstances = self.instanceSetIntersection(requestedInstances, retrievableInstances)
        #TODO Add functionality to sort retrievableInstances into different sets
        #of variables with allowed read access.
        #
        #Returns a list of tuples [([restricted Vars List],[List Of Instances]), dataSetTuple2, ...]
        #dataSetQueriesList = setOperators.segmentDataSetsByPermissions(retrievableInstances, permissionQueryDict)
        #urlParameters = request.query_string
        # print("Got auth, context.user, and queryString data.")
        jsonObj = {}
        try:
            # print("Requested Instances: ", requestedInstances)
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
        # Verbose request logging - commented out for cleaner output
        # print("In Update API execution segment.")
        # print("Request: ", request)
        userAuthInfo = request.auth
        # print("request.auth : ", request.auth)
        (accessQueryDict, permissionQueryDict) = self.getUsersObjectAccessPermissions(userAuthInfo)
        #Check to ensure user has at least some access to updates.
        if(not "U" in accessQueryDict):
            response.status = falcon.HTTP_405
            raise PermissionError("Update requests not allowed at all for this user on this object type.")
        #Determines which variables can be updated.
        if(not "U" in permissionQueryDict):
            response.status = falcon.HTTP_405
            raise PermissionError("Update requests do not have access to any variables on this object type.")
        data = request.get_media()
        singularUpdate = {}
        massUpdateDataSet = []
        for someData in data:
            dataSegment = (someData.data).decode("utf-8")
            #polariId and compositeId are used in the case where you have a single
            #instance that needs updated and sending either a singular string id
            #in the format of a singular polariId
            if(someData.name == "polariId"):
                singularUpdate["polariId"] = dataSegment
            if(someData.name == "compositeId"):
                singularUpdate["compositeId"] = dataSegment
            #A single dictionary that maps variables to be updated to values they
            #should be updated to, used together with either a polariId or a
            #compositeId value.
            if(someData.name == "updateData"):
                singularUpdate["updateData"] = json.loads(dataSegment)
            #A composite of multiple dicts with ids and instance updates paired.
            if(someData.name == "massUpdateDataSet"):
                massUpdateDataSet = json.loads(dataSegment)
        if(singularUpdate != {}):
            massUpdateDataSet.append(singularUpdate)
        response.status = falcon.HTTP_200
        for instUpdate in massUpdateDataSet:
            instToUpdate = None
            if("polariId" in instUpdate):
                instToUpdate = self.manager.objectTables[self.apiObject][instUpdate["polariId"]]
            elif("compositeId" in instUpdate):
                #TODO Build out functionality to handle composite Ids.
                response.status = falcon.HTTP_400
                raise ValueError("Functionality to handle Composite Ids has not been built out yet.")
            else:
                response.status = falcon.HTTP_400
                raise ValueError("Recieved Update request containing instance update with neither a composite or polari Identifier ('polariId' or 'compositeId') value .")
            if("updateData" in instUpdate):
                updateDict = instUpdate["updateData"]
                #TODO For now we just allow everything to be set, need to implement
                #limitation to only allow for variables with polyTypedVar instances
                #accounted for to be added.
                for someVarName in updateDict.keys():
                    setattr(instToUpdate, someVarName, updateDict[someVarName])
            else:
                response.status = falcon.HTTP_400
                raise ValueError("Recieved Update request containing a valid instance id, but no updateData to perform the update with.")

            

    def on_put_collection(self, request, response):
        pass

    #Create object instances in CRUDE
    def on_post(self, request, response):
        print(f"[polariCRUDE] ========== POST request for {self.apiObject} ==========")
        userAuthInfo = request.auth
        #authUser = request.context.user
        urlParameters = request.query_string
        (accessQueryDict, permissionQueryDict) = self.getUsersObjectAccessPermissions(userAuthInfo)
        data = request.get_media()
        dataSets = []
        dataSet = {}
        print(f"[polariCRUDE] Processing multipart data...")
        for someData in data:
            print(f"[polariCRUDE] Field name: {someData.name}, content type: {someData.content_type}")
            dataSegment = (someData.data).decode("utf-8")
            print(f"[polariCRUDE] Field value: {dataSegment}")
            #THE FOLLOWING IS AN EXAMPLE DATASET, where 'attachmentPoints' resolves to a
            #specific set of variables attached to specific instances and 'initParamSets'
            #is a list of keyword parameters which will be passed into the __init__ function
            #of the given class in order to create a new instance of the class.
            #{
            #"attachmentPoints":
            #   {
            #   "varSpecification":[{"obj0":["varName0", "varName1",..]}], "obj1":[..], ..}], 
            #   "instanceQuery":query
            #   }
            #,
            #"initParamSets":
            #   [
            #   {"Inst0param0":value, "Inst0param1":value}, {"Inst1param0":value, "Inst1param1":value}, ..
            #   ]
            #}
            if(someData.name == "attachmentPoints"):
                dataSet["attachmentPoints"] = json.loads(dataSegment)
            if(someData.name == "initParamSets"):
                dataSet["initParamSets"] = json.loads(dataSegment)
            #THIS IS USED IF MULTIPLE DATASETS ARE BEING SENT AT ONCE
            #A list of dataSets with format as stated before [{dataSet0},{dataSet1},...]
            if(someData.name == "dataSets"):
                dataSets = json.loads(dataSegment)
        if(dataSet != {}):
            dataSets.append(dataSet)
        print(f"[polariCRUDE] Final dataSets to process: {dataSets}")
        print(f"[polariCRUDE] CreateRequiredParameters: {self.CreateRequiredParameters}")
        print(f"[polariCRUDE] CreateDefaultParameters: {self.CreateDefaultParameters}")
        allowedUpdatesAccessDict = {}
        allowedUpdatesPermissionsDict = {}
        tempInstancesList = []
        for someDataSet in dataSets:
            #Take given json entries and create a list of temporary instances from it.
            print(f"[polariCRUDE] Processing dataSet: {someDataSet}")
            for newInst in someDataSet["initParamSets"]:
                print(f"[polariCRUDE] Creating instance with params: {newInst}")
                #Use the __init__ funtion for this api's object to create new instances using variables passed.
                #Add the new instances to the list of temporary instances.
                #After all instances are created we will run a query operation on them to ensure the user
                #should be allowed to create them in the given criteria.
                missingRequiredParamsList = list(self.CreateRequiredParameters)
                #Validate that the parameters are valid, record parameters that
                #were not passed in case an error occurs or if they are required.
                for someParam in newInst.keys():
                    if(someParam in self.CreateRequiredParameters):
                        missingRequiredParamsList.remove(someParam)
                        #TODO If the variable or class has strict typing or validation
                        #enabled for it on the PolyTyping, we check the value against
                        #the polyTypedVar or parameter type enforcement info.
                    elif(not someParam in self.CreateDefaultParameters):
                        errMsg = "Error: invalid initialization parameter '"+ someParam + "' passed for class " + self.apiObject + ", should only pass one of the following required valid parameters: " + str(self.CreateRequiredParameters) + " or optional default parameters: " + str(self.CreateDefaultParameters)
                        raise ValueError(errMsg)
                if(len(missingRequiredParamsList) != 0):
                    errMsg = "Error: Missing required parameters for creation of instances of object type '" + self.apiObject + "' missing required parameters are: " + str(missingRequiredParamsList)
                    raise ValueError(errMsg)
                #After validating, create the new instance using the given parameters.
                if("manager" in newInst.keys()):
                    #TODO If manager is defined using an Id, query that manager and
                    #assign the reference to it as the manager instead.  This is
                    #used if multiple managers exist on one system or if this manager
                    #is being used as a relay or intermediary to create on another manager.
                    raise ValueError("The functionality to create instances remotely or for multiple managers on a system has not been implemented.  Do not include 'manager' in create request, it will be set automatically to the manager hosting the server.")
                else:
                    #We assume the manager is the same one hosting the server since
                    #the instance create request is not specified for another manager.
                    print(f"[polariCRUDE] Calling CreateMethod with: {newInst}")
                    print(f"[polariCRUDE] CreateMethod reference: {self.CreateMethod}")
                    newInstance = self.CreateMethod(**newInst, manager=self.manager)
                    print(f"[polariCRUDE] Created instance: {newInstance}")
                    print(f"[polariCRUDE] Instance __dict__: {newInstance.__dict__ if hasattr(newInstance, '__dict__') else 'no __dict__'}")
                    tempInstancesList.append(newInstance)
            # attachmentPoints is optional - only process if provided
            if "attachmentPoints" not in someDataSet:
                continue
            varSpec = someDataSet["attachmentPoints"]["varSpecification"][0]
            for objName in varSpec.keys():
                objVars = varSpec[objName]
                targetQuery = someDataSet["attachmentPoints"]["instanceQuery"][0][objName]
                print("targetQuery: ", targetQuery)
                attachmentInstances = self.manager.getListOfInstancesByAttributes(className=objName, attributeQueryDict=targetQuery)
                print("attachmentInstances: ", attachmentInstances)
                for id in attachmentInstances.keys():
                    for someVar in objVars:
                        attrRef = getattr(attachmentInstances[id], someVar)
                        attrType = attrRef.__class__.__name__
                        if(len(tempInstancesList) > 1):
                            if(attrRef == None):
                                attrRef = tempInstancesList
                            elif(attrType == "polariList" or attrType == "list"):
                                for newInst in tempInstancesList:
                                    attrRef.append(newInst)
                            else:
                                raise ValueError("ERROR: Attempting to add a set of values to ")
                        elif(len(tempInstancesList) == 1):
                            if(attrType == "polariList" or attrType == "list"):
                                attrRef.append(tempInstancesList[0])
                            elif(attrType in self.manager.objectTypingDict.keys()):
                                #TODO Delete the reference if it is a duplicate, migrate main ref if another 
                                #reference exists for the instance being replaced, or delete the reference and
                                #perform a similar action to all referenced nodes dependent on it...
                                #TEMPORARILY we will just replace it and ignore all that though.
                                attrRef = tempInstancesList[0]
                            else:
                                attrRef = tempInstancesList[0]
                        else:
                            raise ValueError("Passed a dataSet that did not create any instances.")
        #With all validation of permissions complete and queries resolved, we return the created instances
        #Return the created instances in the response
        if tempInstancesList:
            response.status = falcon.HTTP_201
            responseData = self.manager.getJSONdictForClass(passedInstances=tempInstancesList)
            print(f"[polariCRUDE] Response data from getJSONdictForClass: {responseData}")
            response.media = {
                self.apiObject: responseData
            }
            print(f"[polariCRUDE] Created {len(tempInstancesList)} instance(s) of {self.apiObject}")
            print(f"[polariCRUDE] ========== POST complete ==========")
        else:
            response.status = falcon.HTTP_200
            response.media = {self.apiObject: {}}
            print(f"[polariCRUDE] No instances created")
            print(f"[polariCRUDE] ========== POST complete (empty) ==========")


    def on_post_collection(self, request, response):
        pass

    #Delete in CRUD
    def on_delete(self, request, response):
        userAuthInfo = request.auth
        urlParameters = request.query_string
        (accessQueryDict, permissionQueryDict) = self.getUsersObjectAccessPermissions(userAuthInfo)
        #Check to ensure user has at least some access to events.
        if(not "D" in accessQueryDict):
            response.status = falcon.HTTP_405
            raise PermissionError("Delete requests not allowed at all for this user on this object type.")
        data = request.get_media()
        targetInfo = {}
        event = ""
        parametersDict = {}
        for someData in data:
            # Verbose data logging - commented out for cleaner output
            # print("data segment name: ",someData.name)
            # print("data segment content type: ",someData.content_type)
            # print("data segment: ", someData.data)
            dataSegment = (someData.data).decode("utf-8")
            #Find if target can be found using passed variable info.
            #If the variables passed in do not resolve to exactly one target,
            #then throw an error.
            if(someData.name == "targetInstance"):
                targetInfo = json.loads(dataSegment)
        allowedInstances = self.manager.getListOfInstancesByAttributes(className=self.apiObject, attributeQueryDict=accessQueryDict["D"][self.apiObject] )
        targetResolution = self.manager.getListOfInstancesByAttributes(className=self.apiObject, attributeQueryDict=targetInfo )
        targetInstance = None
        instancesDeleted = None
        migratedInstances = None
        #First, check if the target info passed can resolve to a single target.
        if(targetInfo == {}):
            raise KeyError("No target Information passed for use in retrieving target.")
        if(len(targetResolution) == 1):
            targetId = list(targetResolution.keys())[0]
            targetInstance = targetResolution[targetId]
            if(targetId not in allowedInstances.keys()):
                raise PermissionError("Access Permissions do not allow user to delete the targeted instance.")
            (instancesDeleted, migratedInstances) = self.manager.deleteTreeNode(className=self.apiObject, nodePolariId=targetId)
        else:
            if(len(targetResolution) == 0):
                raise ValueError("Target did not resolve and could not retrieve any instances.")
            else:
                raise ValueError("Target resolved for multiple instances, must resolve to only one.")
        response.media = {"instancesDeleted":instancesDeleted,"migratedInstances":migratedInstances}
        #Take the return value and convert it to a format that can be 
        response.status = falcon.HTTP_200

    def on_delete_collection(self, request, response):
        pass

    def on_event(self, request, response):
        # Verbose request logging - commented out for cleaner output
        # print("In Event API execution segment.")
        # print("Request: ", request)
        userAuthInfo = request.auth
        # print("request.auth : ", request.auth)
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
            # Verbose data logging - commented out for cleaner output
            # print("data segment name: ",someData.name)
            # print("data segment content type: ",someData.content_type)
            # print("data segment: ", someData.data)
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
        allowedInstances = self.manager.getListOfInstancesByAttributes(className=self.apiObject, attributeQueryDict=accessQueryDict["E"][self.apiObject] )
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