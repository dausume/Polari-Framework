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
        self.permissionSets = []
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
            return {'R':{self.apiObject:"*"}}, {'R':([],{self.apiObject:"*"})}
        #Get the user and compile a permissions dictionary for the object based on
        #the permissions tied to the user.
        else:
            return {'R':{self.apiObject:"*"}}

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
        elif(not "R" in permissionQueryDict):
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
    def onChannelValidation(self):
        #Does the Channel allow for the particular CRUD action to be performed?
        pass
    #
    def onObjectValidation(self):
        #Does the user have
        pass