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

#Defines the Create, Read, Update, and Delete Operations for a particular api endpoint designated for a particular dataChannel or polyTypedObject Instance.
class polariAPI(treeObject):
    @treeObjectInit
    def __init__(self, apiName=None, availableObjectsList=[], allowedMinAccess={'R':{'allObjs':'allVars'}}, allowedMaxAccess={'R':{'allObjs':'allVars'}}):
        #The polyTypedObject or dataChannel Instance
        self.apiName = apiName
        self.permissionSets = []
        self.availableObjectsList = availableObjectsList
        self.permissionsDict = {'C':{}, 'R':{'allObjs':'allVars'}, 'U':{}, 'D':{}}
        #The level of permissions given to anyone trying to access the api.
        self.allowedMinAccess = allowedMinAccess
        #The hiighest level of permissions that can be granted to anyone accessing the api.
        self.allowedMaxAccess = allowedMaxAccess

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
        try:
            jsonArrayToGet = []
            for someObj in self.availableObjectsList:
                jsonObj = self.manager.getJsonDictForClass(passedInstances=[someObj])
                jsonArrayToGet.append(jsonObj)
            print('Returning value for api on get: ', jsonArrayToGet)
            response.context.result = jsonArrayToGet
            print('Set context.result to return value.')
        except Exception as err:
            print('Threw exception in get method.')
            print(err)
            #raise falcon.HTTPServiceUnavailable(
            #    title = 'Service Failure on Manager',
            #    description = ('Encountered error while trying to get objects on given manager.'),
            #    retry_after=60
            #)
        response.set_header('Powered-By', 'Polari')
        print("Setting Header.")
        response.statues = falcon.HTTP_200
        print("Setting HTTP to 200.")
        #if(allObjects == [] or allObjects == None):
        #    response.status = falcon.HTTP_400
        #else:
        #    response.status = falcon.HTTP_200
        

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