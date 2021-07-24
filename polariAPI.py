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
    def __init__(self, apiName, polServer, availableObjectsList=[], objectAvailabilityQueries={}, allowedMinAccess={'R':{'allObjs':'allVars'}}, allowedMaxAccess={'R':{'allObjs':'allVars'}}):
        #The polyTypedObject or dataChannel Instance
        endpointList = polServer.uriList
        if('/' + apiName in endpointList or '\\' + apiName in endpointList):
            raise ValueError("Trying to define an api for uri that already exists on this server.")
        self.apiName = '/' + apiName
        self.permissionSets = []
        self.availableObjectsList = availableObjectsList
        self.availableObjectGroupings = {}
        self.objectAvailabilityQueries = objectAvailabilityQueries
        for someObj in self.availableObjectsList:
            isValidObj = False
            if(someObj.__class__.__name__ == "treeObject" or someObj.__class__.__name__ == "managerObject"):
                isValidObj = True
            else:
                for someParentClass in someObj.__class__.__bases__:
                    if(someParentClass.__name__ == "treeObject" or someParentClass.__name__ == "managerObject"):
                        isValidObj = True
                        break
            if(not isValidObj):
                errMsg = "Invalid value passed into polariAPI " + str(someObj) + " which has parent objects - "+ str(someObj.__class__.__bases__) + " must be either an instance of type treeObject or managerObject or have one of those objects as a parent class & decorator for __init__()."
                raise ValueError(errMsg)
            #if(someObj.__class__.__name__ in self.availableObjectGroupings.keys()):
            #    self.availableObjectGroupings[someObj.__class__.__name__]
        self.permissionsDict = {'C':{}, 'R':{'allObjs':'allVars'}, 'U':{}, 'D':{}}
        #The level of permissions given to anyone trying to access the api.
        self.allowedMinAccess = allowedMinAccess
        #The hiighest level of permissions that can be granted to anyone accessing the api.
        self.allowedMaxAccess = allowedMaxAccess
        if(polServer != None):
            polServer.falconServer.add_route(self.apiName, self)

    #Read in CRUD
    def on_get(self, request, response):        
        #Get the authorization data, user data, and potential url parameters, which are both commonly relevant to both cases.
        print("Starting GET method.")
        authSession = request.auth
        print("request.auth : ", request.auth)
        #authUser = request.context.user
        print("request.context : ", request.context)
        print("request.query_string : ", request.query_string)
        #urlParameters = request.query_string
        print("Got auth, context.user, and queryString data.")
        for someClassType in self.objectAvailabilityQueries.keys():
            currentQuery = self.objectAvailabilityQueries[someClassType]
        try:
            jsonArrayToGet = []
            for someObj in self.availableObjectsList:
                jsonObj = self.manager.getJSONdictForClass(passedInstances=[someObj])
                jsonArrayToGet.append(jsonObj)
            #print('Returning value for api on get: ', jsonArrayToGet)
            response.media = jsonArrayToGet
            #print('Set context.result to return value.')
            response.status = falcon.HTTP_200
            #print("Staus set to 200 - Success")
        except Exception as err:
            response.status = falcon.HTTP_500
            print('Threw exception in get method.')
            print(err)
        response.append_header('Powered-By', 'Polari')
        

    async def on_get_collection(self, request, response):
        pass

    #Update in CRUD
    async def on_put(self, request, response):
        pass

    async def on_put_collection(self, request, response):
        pass

    #Create a single object instance in CRUD
    async def on_post(self, request, response):
        pass

    async def on_post_collection(self, request, response):
        pass

    #Delete in CRUD
    async def on_delete(self, request, response):
        pass

    async def on_delete_collection(self, request, response):
        pass