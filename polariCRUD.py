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

#Defines the Create, Read, Update, and Delete Operations for a particular api endpoint designated for a particular dataChannel or polyTypedObject Instance.
class polariCRUD(treeObject):
    @treeObjectInit
    def __init__(self, apiObject, polServer):
        endpointList = self.polServer.uriList
        if('/' + apiObject in endpointList or '\\' + apiObject in endpointList):
            raise ValueError("Trying to define an api for uri that already exists on this server.")
        #The polyTypedObject or dataChannel Instance
        self.apiObject = apiObject
        self.permissionSets = []
        #Set default or public permissions for the object.  These can be added on to by individual
        #or group permissions granted to users.
        self.publicPermissions = None
        #Records whether the object is a 'polyTypedObject' or a 'dataChannel'
        self.objType = type(apiObject).__name__
        #Defines whether or not the object's home is not accessable on this server and thus must have a re-direct performed to complete the action.
        self.isRemote = self.apiObject.isRemote
        #Ensures the polariCRUD object has a manager that is the same as the manager of it's apiObject.
        self.manager = (self.apiObject).manager

    #Read in CRUD
    def on_get(self, request, response):
        #Get the authorization data, user data, and potential url parameters, which are both commonly relevant to both cases.
        authSession = request.auth
        authUser = request.context.user
        
        urlParameters = request.query_string
        try:
            allObjects = self.manager.getListOfClassInstances(className=self.apiObject)
        except Exception as err:
            print(err)
            #raise falcon.HTTPServiceUnavailable(
            #    title = 'Service Failure on Manager',
            #    description = ('Encountered error while trying to get objects on given manager.'),
            #    retry_after=60
            #)
        if(self.objType == 'polyTypedObject'):
            allVars = self.apiObject.polyTypedVars
        elif(self.objType == 'dataChannel'):
            allObjects = self.apiObject
        response.set_header('Powered-By', 'Polari')
        #if(allObjects == [] or allObjects == None):
        #    response.status = falcon.HTTP_400
        #else:
        #    response.status = falcon.HTTP_200
        response.context.result = allObjects

    def on_get_collection(self, request, response):
        pass

    #Update in CRUD
    def on_put(self, request, response):
        authSession = request.auth
        authUser = request.context.user
        urlParameters = request.query_string
        #if(self.objType == 'polyTypedObject'):
            #
        #elif(self.objType == 'dataChannel'):
            #

    def on_put_collection(self, request, response):
        pass

    #Create a single object instance in CRUD
    def on_post(self, request, response):
        authSession = request.auth
        authUser = request.context.user
        urlParameters = request.query_string
        #if(self.objType == 'polyTypedObject'):
            #
        #elif(self.objType == 'dataChannel'):
            #

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

    #
    def onChannelValidation(apiType):
        #Does the Channel allow for the particular CRUD action to be performed?
        self.apiObject
    #
    def onObjectValidation(apiType):
        #Does the user have 
        self.apiObject