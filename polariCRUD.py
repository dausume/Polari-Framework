from objectTreeDecorators import *

#Defines the Create, Read, Update, and Delete Operations for a particular api endpoint designated for a particular dataChannel or polyTypedObject Instance.
class polariCRUD(treeObject):
    @treeObjectInit
    def __init__(self, apiObject):
        #The polyTypedObject or dataChannel Instance
        self.apiObject = apiObject
        #Records whether the object is a 'polyTypedObject' or a 'dataChannel'
        self.objType = type(apiObject).__name__
        #Defines whether or not the object's home is not accessable on this server and thus must have a re-direct performed to complete the action.
        self.isRemote = self.apiObject.isRemote
        #Ensures the polariCRUD object has a manager that is the same as the manager of it's apiObject.
        self.manager = (self.apiObject).manager

    #Read in CRUD
    async def on_get(self, request, response):
        #Get the authorization data, user data, and potential url parameters, which are both commonly relevant to both cases.
        authSession = request.auth
        authUser = request.context.user
        urlParameters = request.query_string
        if(self.objType == 'polyTypedObject'):
            allVars = self.apiObject.polyTypedVars
        elif(self.objType == 'dataChannel'):
            allObjects = self.apiObject

    async def on_get_collection(self, request, response):
        pass

    #Update in CRUD
    async def on_put(self, request, response):
        authSession = request.auth
        authUser = request.context.user
        urlParameters = request.query_string
        #if(self.objType == 'polyTypedObject'):
            #
        #elif(self.objType == 'dataChannel'):
            #

    async def on_put_collection(self, request, response):
        pass

    #Create in CRUD
    async def on_post(self, request, response):
        authSession = request.auth
        authUser = request.context.user
        urlParameters = request.query_string
        #if(self.objType == 'polyTypedObject'):
            #
        #elif(self.objType == 'dataChannel'):
            #

    async def on_post_collection(self, request, response):
        pass

    #Delete in CRUD
    async def on_delete(self, request, response):
        authSession = request.auth
        authUser = request.context.user
        urlParameters = request.query_string
        #if(self.objType == 'polyTypedObject'):
            #
        #elif(self.objType == 'dataChannel'):
            #

    async def on_delete_collection(self, request, response):
        pass

    #
    def onChannelValidation(apiType):
        #Does the Channel allow for the particular CRUD action to be performed?
        self.apiObject
    #
    def onObjectValidation(apiType):
        #Does the user have 
        self.apiObject