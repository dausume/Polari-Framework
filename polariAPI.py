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
from falcon import falcon
from polariPermissionSet import polariPermissionSet
from inspect import isclass
import json

#Defines the Create, Read, Update, and Delete Operations for a particular api endpoint designated for a particular dataChannel or polyTypedObject Instance.
class polariAPI(treeObject):
    @treeObjectInit
    def __init__(self, apiName, polServer, minAccessDict={}, maxAccessDict={}, minPermissionsDict={}, maxPermissionsDict={}):
        #The polyTypedObject or dataChannel Instance
        endpointList = polServer.uriList
        if('/' + apiName in endpointList or '\\' + apiName in endpointList):
            raise ValueError("Trying to define an api for uri that already exists on this server.")
        self.apiName = '/' + apiName
        self.permissionSets = []
        #C-Create, R-Read, U-Update, D-DELETE, E-Event
        #
        #Create Access: Restricts values that may be entered into an instance during
        #creation.  If instance does not meet query criteria in 'C' segment, instance
        #cannot be created.
        #Read Access: Restricts instances returned with a GET to those returned by the
        #given classes and their queries.
        #Update Access: Restricts instances that are able to be updated using a PUT
        #request to only those returned by given classes and their queries.
        #Delete Access: Restricts instances that are able to be deleted using a DELETE
        #request to only those returned by given classes and their queries.
        #Event Access: Restricts which instances may have their events/functions
        #triggered down to those that are retrieved by the query.
        # Normal Formatting - {'C':{}, 'R':{}, 'U':{}, 'D':{}, 'E':{}}
        self.minAccessDict = minAccessDict
        self.maxAccessDict = maxAccessDict
        #Create Permissions: Restricts which fields may be passed during the creation
        #of a given object instance.
        #Read Permissions: Restricts which fields may be retrieved using a GET request.
        #Update Permissions: Restricts which fields may be updated via a PUT request.
        #Delete Permissions: Restricts the ability to do chain-deletion stemming from
        #the given object from a given field, this also interferes with certain PUT or
        #update rquests which would happen to remove the final reference to a given object.
        #Event Permissions: Restricts what events on a given instance is allowed as well
        #as which parameters may be passed to a given event
        #Normal Formatting - {'C':{}, 'R':{}, 'U':{}, 'D':{}, 'E':{}}
        self.minPermissionsDict = minPermissionsDict
        self.maxPermissionsDict = maxPermissionsDict
        if(polServer != None):
            polServer.falconServer.add_route(self.apiName, self)

    def validate_AccessDict(self, accessDict):
        for CRUDEsegment in accessDict:
            if(not CRUDEsegment in ['C', 'R', 'U', 'D', 'E']):
                raise ValueError("Entered invalid value for CRUDE Permissions segment.")
        for CRUDEsegment in accessDict:
            for instanceType in accessDict[CRUDEsegment]:
                #Validate instance type has a valid PolyTyping Instance on the manager.
                if not instanceType in self.manager.objectTypingDict.keys():
                    errMsg = "Entered invalid type "+ instanceType + " into CRUDE Access Query, type must be accounted for in PolyTyping object instance."
                    raise ValueError(errMsg)
                typingInstance = self.manager.objectTypingDict[instanceType]
                for attributeName in accessDict[CRUDEsegment][instanceType]:
                    #Validate the Attribute exists as a PolyTypedVariable on the PolyTyping Instance
                    if not attributeName in typingInstance.variableNameList:
                        errMsg = "Could not find attribute '"+ attributeName + "' accounted for in the PolyTyping for the type"
                        raise ValueError(errMsg)
                        for someAttributeQuerySegment in accessDict[CRUDEsegment][instanceType][attributeName]:
                            if not (someAttributeQuerySegment == "*"):
                                errMsg = "Invalid Query segment '"+ someAttributeQuerySegment + "' under the attribute '" + attributeName + "' for the type '" + instanceType + "' within an Access Query under the segment '" + CRUDEsegment + "'"
                                raise ValueError(errMsg)
                            if type(someAttributeQuerySegment).__name__ == 'dict':
                                for queryCondition in someAttributeQuerySegment.keys():
                                    if not queryCondition in ['EQUALS', 'CONTAINS', 'IN']:
                                        errMsg = "Invalid Query Condition Section '"+ queryCondition +"' in Query segment '"+ someAttributeQuerySegment + "' under the attribute '" + attributeName + "' for the type '" + instanceType + "' within an Access Query under the segment '" + CRUDEsegment + "'"
                                        raise ValueError(errMsg)


    def validate_PermissionsDict(self):
        print("hi")

    #Read in CRUD
    def on_get(self, request, response):
        if(not "R" in self.minAccessDict.keys()):
            response.status = falcon.HTTP_405
            raise PermissionError("Read or Get requests not allowed on this API.")
        jsonObj = {}
        #Get the authorization data, user data, and potential url parameters, which are both commonly relevant to both cases.
        print("Starting GET method.")
        authSession = request.auth
        print("request.auth : ", request.auth)
        #authUser = request.context.user
        print("request.context : ", request.context)
        print("request.query_string : ", request.query_string)
        #urlParameters = request.query_string
        print("Got auth, context.user, and queryString data.")
        #TODO Finish incorporating new query functionality
        tempDict = {}
        try:
            if(len(self.minAccessDict) > 0):
                for someObjType in self.minAccessDict["R"].keys():
                    curQuery = self.minAccessDict["R"][someObjType]
                    print("For type ",someObjType, " using query - ",curQuery)
                    passedInstances = self.manager.getListOfInstancesByAttributes(className=someObjType, attributeQueryDict=curQuery )
                    if(passedInstances != {}):
                        jsonObj[someObjType] = self.manager.getJSONdictForClass(passedInstances=passedInstances)
                    else:
                        jsonObj[someObjType] = {}
            #print('Returning value for api on get: ', jsonArrayToGet)
            response.media = [jsonObj]
            #print('Set context.result to return value.')
            response.status = falcon.HTTP_200
            #print("Staus set to 200 - Success")
        except Exception as err:
            response.status = falcon.HTTP_500
            print('Threw exception in get method.')
            print(err)
        response.append_header('Powered-By', 'Polari')
        

    def on_get_collection(self, request, response):
        if(not "R" in self.allowedMinAccess.keys()):
            response.status = falcon.HTTP_405
            raise PermissionError("Read or Get requests not allowed on this API.")
        pass

    #Update in CRUD
    def on_put(self, request, response):
        if(not "U" in self.allowedMinAccess.keys()):
            response.status = falcon.HTTP_405
            raise PermissionError("Update or Put requests not allowed on this API.")
        pass

    def on_put_collection(self, request, response):
        if(not "U" in self.allowedMinAccess.keys()):
            response.status = falcon.HTTP_405
            raise PermissionError("Update or Put requests not allowed on this API.")
        pass

    #Create a single object instance in CRUD
    def on_post(self, request, response):
        if(not "C" in self.allowedMinAccess.keys()):
            response.status = falcon.HTTP_405
            raise PermissionError("Create or Post requests not allowed on this API.")
        pass

    def on_post_collection(self, request, response):
        if(not "C" in self.allowedMinAccess.keys()):
            response.status = falcon.HTTP_405
            raise PermissionError("Create or Post requests not allowed on this API.")
        pass

    #Delete in CRUD
    def on_delete(self, request, response):
        if(not "D" in self.allowedMinAccess.keys()):
            response.status = falcon.HTTP_405
            raise PermissionError("Delete requests not allowed on this API.")
        pass

    def on_delete_collection(self, request, response):
        if(not "D" in self.allowedMinAccess.keys()):
            response.status = falcon.HTTP_405
            raise PermissionError("Delete requests not allowed on this API.")
        pass