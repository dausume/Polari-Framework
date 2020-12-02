import falcon

class fakeChannel:
    def __init__(self):
        self.name = 'fakeChannel'
        self.fakeChannelJSON = [
            {
                "class":"fakeChannel",
                "manager":("managerClassName", "managerIdentifiers"),
                "source":("sourceClassName", "sourceIdentifiers"),
                "create":False,
                "read":True,
                "update":False,
                "delete":False,
                "filter":"*",
                "sinks":[("sourceClassName", "sourceIdentifiers")],
                "data":[
                    {
                        "name":"fakeChannel"
                    }
                ]
            },
            {
                "class":"testApiChannelServer",
                "manager":("managerClassName", "managerIdentifiers"),
                "source":("sourceClassName", "sourceIdentifiers"),
                "create":False,
                "read":True,
                "update":False,
                "delete":False,
                "filter":"*",
                "sinks":[("sourceClassName", "sourceIdentifiers")],
                "data":[
                    {
                        "name":"fakeServer"
                    }
                ]
            }
        ]

class fakeUser:
    def __init__(self, userName):
        self.userName = userName
        self.objPermissions = [
            {
                "source":("sourceClassName", "sourceIdentifiers"),
                "class":"fakeChannel",
                "filter":"*",
                "create":False,
                "read":True,
                "update":False,
                "delete":False
            },
            {
                "source":("sourceClassName", "sourceIdentifiers"),
                "class":"testApiChannelServer",
                "filter":"*",
                "create":False,
                "read":True,
                "update":False,
                "delete":False
            }
        ]
        #Sets the access to the channel to the default values.
        #If totalAccess is false, then their object permissions are analyzed.
        #If their object permissions match to all of the objects in the channel, then
        #totalAccess will be set to true.
        self.channelPermissions = [
            {
                "source":("sourceClassName", "sourceIdentifiers"),
                "name":"fakeChannel",
                "id":"09gUmDhrP",
                "totalAccess":False
            }
        ]

class fakeCRUD:
    def __init__(self, apiObject):
        #The polyTypedObject or dataChannel Instance
        self.apiObject = apiObject
        #Records whether the object is a 'polyTypedObject' or a 'dataChannel'
        self.objType = type(apiObject).__name__

class testApiChannelServer:
    def __init__(self):
        self.name = "fakeServer"
        self.apiServer = falcon.API()
        templateURI = '/manager-' + 'testManager' + '_' + 'name-testManager~id-ab89HqDPd' + '_/channel/' + self.serverChannel.name
        print('Template URI: ', templateURI)
        self.apiServer.add_route(uri_template = templateURI, resource= fakeCRUD(self.serverChannel) )